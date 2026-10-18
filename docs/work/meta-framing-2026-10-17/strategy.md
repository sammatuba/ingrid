# Decision: the meta problem leads with accountability, not belief maintenance

Status: strategy record, 2026-10-17. Orchestrator seat (Claude Opus 5.5) with the guardian seat
(Claude Fable, read-only advice, same session). Owner: Sam. Builds on the
[entry framing record](../entry-framing-2026-10-17/strategy.md) (theory, then domain, then build),
which stands; this record changes only the headline of the theory tier.

## Question from the owner

"Saying that knowledge work is belief maintenance is too narrow. How do we frame it in a more
business- or impact-centric or social manner?" The owner also states the order: the AI problem is
the meta problem, the future of work is its category, and the Philippine power market is the domain
application. Fix the surfaces accordingly.

## Decision

The meta problem is an accountability problem. Its headline:

> **Who answers for a decision made with AI?**

The statement, in plain words:

AI can now read every signal and draft every change. People still decide, and people still answer
for the result. An organization that cannot show which AI judgment it trusted, and why, has two bad
choices. It holds AI back and loses the work AI could do. Or it uses AI blind and takes decisions that
nobody can explain or learn from. Trust and traceability come from records, not from models. We test
this in the Philippine wholesale electricity market. There, evidence carries a time stamp, rules come
from a regulator, and the truth settles every month.

The owner's line stays under the headline as its domain translation: *from market signals to
trustworthy, traceable decisions*.

The same problem at three levels, each with its evidence grade:

| Level | The problem | Grade |
|---|---|---|
| People (the work) | AI moves the human job from finding and reading information to judging it and answering for it. | framing; no analyst-effect measure exists (experiment 3) |
| Organization (the business) | Without trust an organization holds AI back; without traceability it uses AI blind. Both cost money: lost work, or decisions nobody can explain, review or learn from (the whiteboard's "blame game"). | belief; first numbers VAL-1 (median 8.5 h schedule lag on the typed pass; the first pass gave 20.7 h) and PROJ-1 only; incidence absent |
| Sector (the social stake) | In an essential, regulated sector, a board and a regulator must see who decided what, on which evidence, and when. | readers named by the owner (board first, regulator or counterparty second); never observed |

Belief maintenance stays as the mechanism, not the headline: it is proposition 1 of the
[meta thesis](../../architecture/meta-thesis-and-framework.md), the knowledge layer of the four-question
loop on the [theoretical foundation](../../architecture/theoretical-foundation.md), and the second
paragraph of [START-HERE](../../START-HERE.md).

Three roles, so the domain record and the meta record agree: the **problem** is trusting and answering
for decisions made with AI; the **product** is the record structure that makes that possible; the
**model** is the worker inside it and never the record of it. The domain record's sentence "The AI
judgment ... is not the product" is consistent with this and stays; a clarifying sentence goes next to it.

## Rejected

- "AI makes decisions faster; the problem is making them accountable." Rejected by the guardian: the
  AI never decides in this system. The problem is answering for decisions made *with* AI.
- "Accountable decisions at AI speed" as a headline. It is a productivity claim, and every
  productivity sentence is a hypothesis until experiment 3 runs. Usable only as "we test whether".
- A consumer-price or public-interest claim ("the prices people pay"). No record in the repository
  supports it. The sector level names the board and the regulator only.

## Surfaces changed in this round

| Surface | Change |
|---|---|
| [meta thesis](../../architecture/meta-thesis-and-framework.md) §1 | opens on the accountability problem; belief maintenance becomes the mechanism sentence |
| [future-of-work case](../../competition/ai-builder-cup-2026/future-of-work-case.md) §1 | heading and first paragraph lead with the accountability problem and the three levels |
| [START-HERE](../../START-HERE.md) | first paragraph opens on the headline question |
| [README](../../../README.md) | opens on the meta problem, then the desk as its test |
| [AGENTS.md](../../../AGENTS.md) mission | one sentence for the meta problem, word-neutral (bootstrap budget 1400) |
| [problem statement 2026-10-17](../../product/problem-statement-2026-10-17.md) | a meta problem paragraph above the whiteboard |
| [problem and thesis](../thesis-challenge-2026-10-16/problem-and-thesis.md) | the three-roles sentence beside "not the product" |
| [story and script](../../competition/ai-builder-cup-2026/story-and-script.md) | Positioning, 30-second pitch, narration draft opening and deck list line 1 open on the headline question |
| [deck](../../competition/ai-builder-cup-2026/deck.md) cover front matter | general claim reworded; slides untouched |
| [paper](../../product/paper-accountable-ai-decisions-2026-10-17.md) (added later the same day) | an arXiv-style paper on this framing, with graded measurements; uses the typed VAL-1 median of 8.5 h |

Not changed: deck slides 1 to 12 (accepted at REL-2 and REL-4; slide 1 bullet 2 still says "gone
stale", a known leftover), the explainer chapters. They state the records claim, which stands; the
headline question can reach them after submission. The [shot list](../../competition/ai-builder-cup-2026/video-shotlist.md)
shot 1 narration is re-aligned to the narration draft (53 words, up from 46); the owner records the
video (REL-6) and measures the timing.

## Verification (2026-10-17, on main ae0ec08, uncommitted)

- `/usr/bin/python3 scripts/repo.py check`: PASS, bootstrap 1400 of 1400 words.
- `/usr/bin/python3 scripts/plan.py check`: OK, 100 tasks, 8 gates.
- `/usr/bin/python3 -m unittest discover -s tests`: 2004 tests, OK (31 skipped), run before the
  shot list edit; that edit touches Markdown only.
- Review: none yet. The guardian advised before the edits; no independent reviewer has read the diff.

## Material unknowns, and what would change this

- **Analyst effect.** No measure of time, missed issues or rework exists. Experiment 3 would turn the
  people and organization levels from framing into finding, or refute them.
- **Incidence.** Whether misses come from out-of-date assumptions more than from the model. The first
  scored month with attributions (November to December 2026) decides it. If near zero, the
  organization level narrows to "decisions nobody can review".
- **One full trace.** No real case runs evidence → belief → decision → consequence. The PEDC case
  records no analyst decision. Until one does, "answer for the decision" is a design property, not a
  demonstrated one.
- **The readers.** No board or regulator has read the records. A first reading by either would test
  the sector level.
- The owner may prefer a social stake broader than board and regulator. That needs a sourced record
  first (for example, a regulator document on retail pass-through).
