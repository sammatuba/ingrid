# Explainer

The explainer is a guided walk through InGRID for people. It has three parts and 27
chapters. The third part is a companion to the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md).

The first part opens on the ideas: four chapters take the four questions behind the desk. The
system that carries them closes the part. It holds the figures, every component on one map, the
path through the chapters and the two Gemini roles.

The next six chapters are the desk, one layer per chapter. The last sixteen follow the paper,
section by section. Each one names its paper sections in a box at the top, with links to the paper
page. Then it walks the method step by step on the two real cases, and it ends with a self-check.
Two showcases replay the driver card and the recorded judgment with the paper's own values. Six
figures come from the paper's own diagram text.

Each chapter has interactive elements, a self-check question and a strip. The strip shows the
same system in small, with the components that chapter adds. Every special word is in the
[glossary](../glossary.md).

## Open it

On the site: `https://ingrid-desk.web.app/explain`. From the repository: open
[index.html](index.html) in a browser. It works from disk and loads nothing from the network.
On a phone, the chapter list scrolls sideways. Use the arrow keys to move between chapters.

## The chapters

**The ideas**

1. [What we know](00-ideas-1-know.md)
2. [What we do](00-ideas-2-do.md)
3. [Who does what](00-ideas-3-who.md)
4. [How we learn](00-ideas-4-learn.md)
5. [The system that carries these ideas](00-system.md)

**The desk**

6. [Why a review desk exists](01-why.md)
7. [The Philippine grid and the market](02-grid.md)
8. [Evidence, assumptions and cutoff times](03-evidence.md)
9. [The judgment and the decision](04-judgment.md)
10. [Where it runs](05-runs.md)
11. [How we work](06-work.md)

**The paper, step by step**

12. [How to read the paper with this companion](07-paper-guide.md)
13. [One time contract](08-time-contract.md)
14. [From a signal to a scored decision](09-signal-to-decision.md)
15. [Showcase: the driver card and the alert](10-driver-card.md)
16. [Showcase: the recorded judgment](11-judgment-showcase.md)
17. [The compiler and the review transaction](12-compiler-and-transaction.md)
18. [From answers to a label](13-rules-and-receipt.md)
19. [Methods and models](14-methods-and-models.md)
20. [From user stories to desk questions](15-requirements.md)
21. [Measurements, step by step](16-measurements.md)
22. [Four layers and seven record kinds](17-layers-and-records.md)
23. [Governed generative views](18-generated-views.md)
24. [The theories behind the design](19-grounding.md)
25. [Null results, the evaluation plan and the limits](20-evaluation-and-honesty.md)
26. [Behind the prototype: the data and the event map](21-data-and-event-map.md)
27. [Behind the prototype: where it runs](22-hosting-in-depth.md)

## How the page is built

The chapters are the source of truth. The script `scripts/docs/build_explainer.py` turns them and
the glossary into four files. One is `index.html` here. The other three are `explain.html`,
`explain.css` and `explain.js` under `src/grid/`, the page the site serves at `/explain`.

Three parts of the chapter that closes the ideas part come from data inside that script, not from
the chapter file. The figures count the node data at build time. The systems map holds every component from the
[systems inventory record](../work/docs-for-people/systems-inventory-2026-10-15.md), in four
bands, with the flows drawn as arrows.

The path and the chapter strips come from one table of chapter lines and components. The same
system grows chapter by chapter. The test `tests/test_explainer.py` reads the record. It refuses
a status word that differs from it, and a source link that is not in the repository. Change the
record first, then the script.

The site version keeps no inline code, because the site's security policy admits none. The script uses only the Python
standard library. The test `tests/test_explainer.py` fails when any built file differs from a
fresh build. To rebuild:

```sh
/usr/bin/python3 scripts/docs/build_explainer.py
```

The site serves no Markdown. On the served page, every link to a record becomes a reference. The
record keeps its name. Its path in the repository takes the place of the link. One note at the top
of the page says where the records live. The copy here keeps its working links.

Markers inside a chapter place the interactive parts. `<!-- widget: name -->` places one of the
widgets that the script defines. `<!-- paper: 3.4 3.5 -->` draws the box of paper sections. The
script reads the section titles and the figures from the paper file itself. A block between `<!-- quiz -->` and `<!-- /quiz -->` becomes a
self-check question. The glossary words get a definition on hover, once per chapter.

## Who may see it

2026-10-18: the export decision is now in REL-5. See the [export proposal](../work/polish-2026-10-18/export-proposal.md).

The chapters quote figures from the company's data copy, under the owner's permission record, and
link the case pack. The explainer stays inside this private repository. Whether it joins the
public export is a decision for the export task, REL-5.
