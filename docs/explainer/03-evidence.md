# Evidence, assumptions and cutoff times

This chapter explains the three ideas that make the desk honest about time. Everything else in the
method builds on them.

## Evidence has a clock

A piece of evidence is a source, a passage in it, and the moment it became known. The desk never
drops the clock. NGCP posted the trip notice at 13:39 on 21 September 2026, five minutes after the
trip itself. The return notice came at 15:55, 48 minutes after the unit came back. A person who
read only the notices knew about the trip at 13:39, not at 13:34.

The desk also records where each passage came from, and whether a later notice only repeats an
earlier one. Two notices that say the same thing are one fact, not two.

## An assumption has a value, a time span and a source

The assumption in our case reads: "PEDC Unit 2 holds its registered maximum of 83.7 MW on
21 September 2026." It has an entity, a value with a unit, a day, and a source: the register.
The desk accepted it at the start of the day. That acceptance is the first line of the history.

An assumption is a position the analyst holds, not a measured fact. The desk keeps the two apart.
The trip does not prove the assumption false for the whole day. It proves that the day did not go
as assumed.

## The cutoff time

The desk judges a case at a cutoff time. At that moment it stops reading. Only evidence known
before the cutoff may enter the judgment. The desk judges each new notice twice: one second before
the notice became known, and one second after. The difference between the two judgments is the
effect of that one notice.

<!-- widget: cutoff-pair -->

This pair is the core trick. It stops the AI from reading the future. When the desk asks about the
trip, the model cannot see the return notice, because at 13:39 nobody could. It also gives the
analyst a clean before-and-after view of every notice.

## Why identity matters

A notice names a unit by a code or by a name. The register names it by another code. The desk
keeps a reviewed table that joins them. If the table has no match, the judgment stops with "cannot
tell", and no assumption changes. A fuzzy name match never counts as the same unit.

<!-- quiz -->
Q: The desk judges the trip at 13:39:37. Which evidence may the model read?
- All four notices of the day
- [x] The register and the trip notice only
- The register only
Why: NGCP posted the return notice at 15:55. At 13:39 nobody knew it, so the desk hides it from the model.
<!-- /quiz -->

## Sources for this chapter

- The notice times, the two cutoff pairs and the assumption: the
  [PEDC case brief](../cases/pedc-u2-2026-09-21/brief.md) and the
  [outlook record](../cases/pedc-u2-2026-09-21/outlook-revision.md).
- Cutoff pairing and strict compilation: the [working paper](../product/working-paper-2026-10-11.md), section 5.4.
