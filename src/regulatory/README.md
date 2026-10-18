# Regulatory structure and amendment lineage

Deterministic, standard-library segmentation of native UTF-8 regulatory text and the
amendment records that place one clause version at a cutoff. No model, no PDF, no network
call and no legal conclusion: effectivity, applicability, precedence and approval come from
supplied metadata and reviewed records, never from words in a document.

`structure.py` is the R0 starter and is unchanged: line-start `Section <n>. <title>`,
uppercase `SECTION` and `Annex <letter>.` headings, exact spans, supplied dates only. The
[BB2 intent](../../docs/work/bb2-regulatory/intent.md) owns its contract and
[its tests](../../tests/test_regulatory_structure.py) are untouched.

## Family grammars

`grammars.parse(source, family)` returns the same `DocumentStructure` the starter returns,
using one heading grammar per document family. `FAMILIES` names them and
`GRAMMAR_REVISIONS` holds each revision string, which reparsing a source returns unchanged.

| Family | Recognised headings | Kinds |
|---|---|---|
| `wesm_rules` | `CHAPTER <n>`; `X.Y` sections; `X.Y.Z` subsections; `X.Y.Z.W...` clauses; `APPENDIX <letter>` or `Appendix <letter><n>.`; `A1.1` appendix sub-units | chapter, section, subsection, clause, appendix, appendix_section |
| `market_manual` | `SECTION <n> <title>`; `X.Y` subsections; `X.Y.Z...` clauses; appendices as above; `Part <n>. <title>`; `Annex "<letter>"` | section, subsection, clause, appendix, part, annex |
| `erc_resolution` | `WHEREAS`; `RESOLVED`; `Section <n>. <title>`; `1.` paragraphs; `X.Y` clauses | whereas, resolved, section, clause |
| `doe_circular` | `SECTION <n>. <title>`; `1.` paragraphs; `X.Y` clauses | section, clause |

A numbered line is recognised only when the text after the number starts a unit: a lower-case
first letter, or a leading `,;:.()`, marks a line that wrapped out of the previous sentence. A
label with a zero or a padded component is not a unit number. Both stay content and carry an
`unrecognized_heading` diagnostic, as does any line beginning with a heading keyword the
grammar knows but did not match. Spans carry `toc_entry` when the line ends in a dot leader or
a page number glued to a word (a contents-list line), `duplicate_label` when the label already
appeared, and `no_recognized_heading` when nothing was recognised. Diagnostics carry character
offsets only: a page number is never invented.

The chapter and appendix title is the next non-blank line when that line holds no lower-case
letter. A clause carries provision text after its label, so its `title` is `None`; a section or
subsection title is the rest of the line. The WESM Rules numbering is not uniform: depth three
holds both subsection headings and provision text (for example `1.4.8`), so a depth-three
span's title can be the first line of a provision — the quoted text is the whole span either
way. The evidence and the counts are in the [task record](../../docs/work/corpus/structure.md).

## Amendment lineage

`RuleRegister(family)` holds one chain of `RuleVersion` records per clause label. A baseline
document parsed by its family grammar yields one version per clause span; an `Amendment` — an
amending source, an identifier, a supplied effective date, a supplied first availability and
the clauses it names, each with an exact locator into the amending source and the `replaces`
version id of the version it supersedes — yields one new version per named clause, linked to
the version the record says it replaces. Locators are validated against the amending source,
so a substituted text is exactly what the document holds at those offsets.

The replacement relationship is supplied metadata, never the order amendments arrive in: a
change must name the version the register holds as the head of that clause's chain. A change
naming an older version would branch the lineage and is refused as conflicting; one naming an
unknown version, or none, as unresolved; and a supplied first availability that ends before
the replaced version became available is refused as contradictory. A clause the amendment does
not name never changes, whatever the document says; a new clause needs `adds_clause=True` (and
then replaces nothing); two changes naming one clause are refused; re-applying an identical
amendment — the same quote, the same replaced version and the same two supplied dates — is
idempotent, while a resubmission whose supplied metadata differs is refused rather than
silently resolved to the stored record, and an earlier revision is never resurrected.

```python
register = RuleRegister('wesm_rules')
register.add_baseline(source, first_availability, effective=None, kinds=('clause',))
register.apply(Amendment(source, 'DOE-DC-2026-01', effective, first_availability, changes))
register.in_force('3.5.4.1', DateMetadata('2026-10-16', 'day', None))
```

`in_force(clause_label, cutoff)` answers the known-then question for one clause: a version is
in force at the cutoff only when both supplied dates place it there — first availability, what
the register could know by the cutoff, and effectivity, what had legal effect by the cutoff —
and every version it replaces is in force there too. It returns that version, the chain that
led to it (each link the supplied replacement of the one before, so the chain never points at
an excluded version), and an `Exclusion` for every version the cutoff did not admit, each with
its reason: `after_cutoff`, `availability_unknown`, `availability_imprecise`,
`not_yet_effective`, `effectivity_unknown`, `effectivity_imprecise`, or
`ancestor_not_in_force` when a version the excluded one replaced is itself not in force. A
version is admitted only when the end of the date's period is not after the end of the cutoff
period, so a month-precision value is placed from the period's real calendar last day — the
28th or the 29th for February, per its own year — and not its first, and an
unknown or too-coarse date is excluded rather than assumed. An unknown cutoff is refused
rather than guessed. This is the same known-then question the
[review core](../review/README.md) answers for passages.

## Tests and the cited excerpts

```sh
/usr/bin/python3 -m unittest tests.test_regulatory_structure tests.test_regulatory_grammars tests.test_regulatory_lineage
```

`tests/test_regulatory_grammars.py` and `tests/test_regulatory_lineage.py` run on synthetic
fixtures marked `SYNTHETIC` and on short cited excerpts of the public rules.
`scripts/corpus/excerpt.py` takes those excerpts from the PEMC compendium under
`.local/corpus/compendium/` with pypdf unpacked at `.local/pylib/`, and writes
`tests/fixtures/regulatory/excerpts.json` with each source file name, page, PDF SHA-256 and the
excerpt text, at most 400 characters each:

```sh
/usr/bin/python3 scripts/corpus/excerpt.py            # rewrite the fixture
/usr/bin/python3 scripts/corpus/excerpt.py --check    # fail if it is stale
/usr/bin/python3 scripts/corpus/excerpt.py --report   # counts and first candidates per document
```

Document bytes never enter the repository. The register is not yet wired to the review core's
`SourceVersion` and `Passage` records or to the corpus acquisition contract (CORP-1, CORP-3).
