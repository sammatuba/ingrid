"""A standard-library checker for the store's SQL files: balanced quotes and named tables.

This is not a SQL parser and does not pretend to be one — it does not know BigQuery's grammar,
type rules or functions. It answers three questions a review can act on, and it answers them
the same way over every file in ``scripts/corpus/bq/``:

1. **Are the literals closed?** Every ``'``, ``"`` and ``` ` ``` literal and every block
   comment must be closed; an unclosed one is reported with its offset.
2. **Are the parentheses balanced?** Counted over the code, with the contents of literals and
   comments excluded, so a bracket in a quoted string is not counted.
3. **Does every table reference a named table?** After ``FROM``, ``JOIN``, ``INTO``,
   ``UPDATE``, ``DELETE FROM``, ``CREATE TABLE`` and the ``ON <table>(`` of a vector index,
   the reference — bare or backticked, with or without a project — must resolve to one of the
   store's tables or to a common-table expression the same statement defines.

A caller that has to make the checker pass by weakening it has found a real defect in the SQL;
the tests plant deliberate defects and require the checker to report them, so this stays a
check rather than a decoration.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

#: Escapes applied to the inside of a literal: these never mean syntax there.
_ESCAPES = {"(": "\x01", ")": "\x02", ";": "\x03"}

_LITERALS = "'\"`"
#: A reference that follows a keyword which can only introduce a table.
_REFERENCE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+((?:`[^`]+`|[A-Za-z_][A-Za-z0-9_$.]*))", re.I)
#: ``CREATE TABLE`` / ``CREATE VIEW``, with the modifiers BigQuery allows between them.
_DECLARED = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"((?:`[^`]+`|[A-Za-z_][A-Za-z0-9_$.]*))", re.I)
#: The table a vector index is built on: the reference is followed by its column list.
_INDEXED = re.compile(r"\bON\s+((?:`[^`]+`|[A-Za-z_][A-Za-z0-9_$.]*))\s*\(", re.I)
#: A CTE name, with the optional column list a recursive CTE carries: ``name(cols) AS (``.
_CTE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^()]*\)\s*)?AS\s*\(", re.I)

#: Words that can follow FROM/JOIN without being a table.
_NOT_TABLES = {"unnest", "table", "select", "with", "lateral", "only", "if"}


@dataclass(frozen=True)
class Problem:
    """One finding: which statement (1-based, 0 for the file), what, and where."""

    statement: int
    kind: str
    detail: str

    def __str__(self):
        return "statement %d: %s: %s" % (self.statement, self.kind, self.detail)


def _clean(text):
    """The text with comments blanked and literal contents made inert, and the findings."""
    problems, out, index, size = [], [], 0, len(text)
    while index < size:
        if text.startswith("--", index):
            end = text.find("\n", index)
            end = size if end < 0 else end
            out.append(" " * (end - index))
            index = end
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                problems.append(Problem(0, "unterminated_comment",
                                        "the block comment at offset %d is not closed" % index))
                out.append(" " * (size - index))
                index = size
                continue
            out.append(" " * (end + 2 - index))
            index = end + 2
            continue
        char = text[index]
        if char in _LITERALS:
            end, closed = index + 1, False
            while end < size:
                if text[end] == char:
                    if char == "'" and text.startswith("''", end):
                        end += 2
                        continue
                    closed = True
                    break
                end += 1
            if not closed:
                problems.append(Problem(0, "unterminated_quote",
                                        "the %s literal at offset %d is not closed"
                                        % (char, index)))
                out.append(" " * (size - index))
                index = size
                continue
            body = "".join(_ESCAPES.get(item, item) for item in text[index + 1:end])
            out.append(char + body + char)
            index = end + 1
            continue
        out.append(char)
        index += 1
    return "".join(out), problems


def split_statements(text):
    """``[(index, statement)]``: statements split on unescaped semicolons outside literals."""
    cleaned, problems = _clean(text)
    parts, start = [], 0
    for position, char in enumerate(cleaned):
        if char == ";":
            parts.append((len(parts) + 1, cleaned[start:position], text[start:position]))
            start = position + 1
    tail = cleaned[start:]
    if tail.strip():
        parts.append((len(parts) + 1, tail, text[start:]))
    elif not parts and not problems:
        parts.append((1, "", ""))
    return parts


def _restore(value):
    return value.replace("\x01", "(").replace("\x02", ")").replace("\x03", ";")


def table_name(reference):
    """The bare table name of a reference: quotes stripped, project and dataset dropped."""
    return reference.strip().strip("`").split(".")[-1].lower()


def parentheses(statement, number):
    """Balance one statement's parentheses, with literal and comment contents excluded."""
    problems, depth = [], 0
    for position, char in enumerate(statement):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                problems.append(Problem(number, "unbalanced_parentheses",
                                        "a closing parenthesis at offset %d has no opener"
                                        % position))
                depth = 0
    if depth:
        problems.append(Problem(number, "unbalanced_parentheses",
                                "%d parenthesis(es) are never closed" % depth))
    return problems


def check(text, tables):
    """Every problem found in one SQL text; an empty list is a pass."""
    problems = []
    cleaned, findings = _clean(text)
    problems.extend(findings)
    known = {name.lower() for name in tables}
    for index, cleaned_statement, _ in split_statements(text):
        problems.extend(parentheses(cleaned_statement, index))
        local = {match.group(1).lower() for match in _CTE.finditer(cleaned_statement)}
        references = [match.group(1) for pattern in (_REFERENCE, _DECLARED, _INDEXED)
                      for match in pattern.finditer(cleaned_statement)]
        for reference in references:
            name = table_name(reference)
            if name in _NOT_TABLES or name in local or name in known:
                continue
            problems.append(Problem(index, "unknown_table",
                                    "%r is not one of the store's tables or a CTE of this "
                                    "statement" % _restore(reference)))
    return problems
