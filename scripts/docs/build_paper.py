"""Build src/grid/paper.html and paper.css from the paper's Markdown, the page the site serves at /paper.

Standard library only. The output is deterministic: the same Markdown gives the same bytes. The page
loads nothing from the network and carries no inline script, so the site's content security policy
holds: the stylesheet travels under the build stamp like the other pages' files. Platform polish
(PP-B4) puts the paper in the reading frame: a contents rail built from the level-two headings, a
reading-progress hairline (both driven by the shared reading.js), section anchors, and each table
and diagram in a figure with its caption.

The Markdown subset is the explainer's (headings, paragraphs, lists, tables, code, links), rendered by
the explainer builder's own functions. Two additions, because the site loads no math or diagram
library:

    $...$ and $$...$$     a small TeX subset written as HTML (sub- and superscripts, a few symbols)
    ```mermaid ... ```     a flowchart of subgraphs drawn as stacked boxes, its edges listed under them

Usage: /usr/bin/python3 scripts/docs/build_paper.py [--check]
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "product" / "paper-accountable-ai-decisions-2026-10-17.md"
SITE = ROOT / "src" / "grid"          # paper.html and paper.css, the page the site serves at /paper
STAMP_TOKEN = "__NOWCAST_STAMP__"     # the server writes the build stamp here (src/api/__init__.py)

_spec = importlib.util.spec_from_file_location("build_explainer", Path(__file__).with_name("build_explainer.py"))
explainer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(explainer)


# ---------------------------------------------------------------- math: a small TeX subset

SYMBOLS = {r"\sum": "∑", r"\in": "∈", r"\le": "≤", r"\ge": "≥", r"\tau": "τ", r"\{": "{", r"\}": "}",
           r"\,": " ", r"\ ": " ", r"\hat p": "p̂"}


def tex(source: str) -> str:
    """One formula as HTML. Escapes first, so a `<` in the formula stays text."""
    s = html.escape(source, quote=False)
    s = re.sub(r"\\(?:mathrm|text)\{([^{}]*)\}", r"\1", s)
    for name, symbol in sorted(SYMBOLS.items(), key=lambda kv: -len(kv[0])):
        s = s.replace(name, symbol)
    for mark, tag in (("_", "sub"), ("^", "sup")):
        s = re.sub(re.escape(mark) + r"\{([^{}]*)\}", rf"<{tag}>\1</{tag}>", s)
        s = re.sub(re.escape(mark) + r"([A-Za-z0-9'])", rf"<{tag}>\1</{tag}>", s)
    if "\\" in s:
        raise SystemExit(f"unsupported TeX in formula: {source}")
    s = re.sub(r"(?<![\w</])([A-Za-z]\u0302?)(?![\w>])", r"<i>\1</i>", s)
    return s.replace(" - ", " − ")


# ---------------------------------------------------------------- diagram: mermaid subgraphs as boxes

def diagram(lines: list[str]) -> str:
    """A `flowchart` of subgraphs: each subgraph a box (in source order) holding its nodes' labels,
    the edges between boxes listed below in words."""
    labels: dict[str, str] = {}
    boxes: list[tuple[str, list[str], list[tuple[str, str]]]] = []
    current: list[str] | None = None
    inner: list[tuple[str, str]] = []
    edges: list[str] = []
    node = re.compile(r"(\w+)\[([^\]]+)\]")
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("flowchart"):
            continue
        m = re.match(r"subgraph\s+\w+\[([^\]]+)\]", line)
        if m:
            current, inner = [], []
            boxes.append((m.group(1), current, inner))
            continue
        if line == "end":
            current = None
            continue
        for key, label in node.findall(line):
            if key not in labels:
                labels[key] = label
                if current is not None:
                    current.append(label)
        if current is not None:
            keys = re.findall(r"\w+", re.sub(r"\|[^|]*\|", "", node.sub(r"\1", line)))
            for left, right in zip(keys, keys[1:]):
                inner.append((labels[left], labels[right]))
        if current is None:
            plain = node.sub(r"\1", line)
            chain = re.split(r"\s*-->\s*", plain)
            for left, right in zip(chain, chain[1:]):
                note = ""
                n = re.match(r"\|([^|]+)\|\s*(\w+)", right)
                if n:
                    note, right = n.group(1), n.group(2)
                left = left.strip()
                right = right.strip()
                text = f"{labels.get(left, left)} → {labels.get(right, right)}"
                edges.append(text + (f" ({note})" if note else ""))
    out = ['<div class="layers">']
    arrow = ' <span class="arrow">→</span> '
    for title, items, links in boxes:
        out.append('<section class="layer">')
        out.append(f'<h4>{html.escape(title)}</h4>')
        targets: dict[str, list[str]] = {}
        for left, right in links:
            targets.setdefault(left, []).append(right)
        sources = [x for x in items if x in targets]
        if not links:
            lines_out = [html.escape(x) for x in items]
        elif all(len(targets[x]) == 1 for x in sources):
            path, start = [], items[0]
            while start:
                path.append(html.escape(start))
                start = targets.get(start, [None])[0]
            lines_out = [arrow.join(path)]
        else:
            lines_out = [html.escape(x) + arrow + " · ".join(html.escape(t) for t in targets[x]) for x in sources]
        out.append("".join(f"<p>{x}</p>" for x in lines_out))
        out.append('</section>')
    out.append('</div>')
    if edges:
        out.append('<p class="edges-title">Links between the layers</p>')
        out.append('<ul class="edges">' + "".join(f"<li>{html.escape(e)}</li>" for e in edges) + "</ul>")
    return "\n".join(out)


# ---------------------------------------------------------------- the page

def body() -> tuple[str, str]:
    """Return (title, article HTML)."""
    text = SOURCE.read_text(encoding="utf-8")
    slots: dict[str, str] = {}

    def slot(markup: str) -> str:
        key = f"PAPERSLOT{len(slots)}X"
        slots[key] = markup
        return key

    def fence(m: re.Match) -> str:
        return "\n" + slot(diagram(m.group(1).splitlines())) + "\n"

    text = text.replace("\\*", slot("*"))
    text = re.sub(r"```mermaid\n(.*?)\n```", fence, text, flags=re.S)
    text = re.sub(r"^\$\$(.+?)\$\$$", lambda m: slot(f'<div class="math">{tex(m.group(1))}</div>'), text, flags=re.M)
    text = re.sub(r"\$([^$\n]+?)\$", lambda m: slot(f'<span class="math">{tex(m.group(1))}</span>'), text)
    article, title, _, _ = explainer.markdown(text, {}, 0, site=True)
    for key, markup in slots.items():
        article = article.replace(f"<p>{key}</p>", markup).replace(key, markup)
    article = re.sub(r'(?<![="])(https://[^\s<]+)', r'<a href="\1">\1</a>', article)
    return title, article


CSS = """/* The working paper (/paper), built by scripts/docs/build_paper.py: do not edit by hand.
   Platform polish (PP-B4): the paper in the reading frame. The shared frame, page head, label and
   sources are the design system's (ui.css, shell.css tokens); this file sets the paper's own
   reading type, its contents rail, the reading-progress hairline (reading.js fills it) and its
   tables and figures. Inter and Plex only. Every rule is scoped under .pp-page, because ui.css
   loads after this file. */
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text)}
body{font:400 13px/1.5 var(--sans);-webkit-font-smoothing:antialiased}
.bar{display:flex;gap:1rem;align-items:center;padding:.6rem 16px;border-bottom:1px solid var(--rule);font:14px var(--sans)}
.bar a{color:var(--link);text-decoration:none}

/* the reading-progress hairline, under the bar */
.pp-progress{position:fixed;z-index:44;left:0;right:0;top:var(--bar-h,var(--gn-bar-h,0px));height:2px;pointer-events:none}
.pp-progress>span{display:block;height:100%;background:var(--accent);transform:scaleX(0);transform-origin:0 50%}

/* the frame: the reading column centred on the page, the contents rail in the left margin, and
   wide tables reaching into the right margin */
.pp-page .pp-layout{display:grid;grid-template-columns:minmax(200px,1fr) minmax(0,672px) minmax(0,1fr);gap:0 48px;align-items:start}
.pp-page .pp-toc{grid-column:1;justify-self:end;width:min(100%,248px)}
.pp-page .pp-main{grid-column:2/4;min-width:0;container-type:inline-size}
.pp-page .pp-head,.pp-page .pp-article>*{max-width:672px}
.pp-page .pp-head{margin-bottom:var(--s-6)}
.pp-page .pp-head h1{font-size:26px;line-height:1.3;letter-spacing:-.015em;text-wrap:balance}
.pp-page .pp-head .gn-label{margin:0 0 var(--s-2)}
.pp-page .pp-head .gn-page-meta{margin-top:var(--s-3)}

.pp-page .pp-toc{position:sticky;top:calc(var(--bar-h,var(--gn-bar-h,0px)) + var(--s-4));max-height:calc(100vh - var(--bar-h,var(--gn-bar-h,0px)) - var(--s-6));overflow-y:auto;overscroll-behavior:contain;padding-bottom:var(--s-4);scrollbar-width:thin}
.pp-page .pp-toc .gn-label{margin:0 0 var(--s-2);padding-left:12px}
.pp-page .pp-toc ol{list-style:none;margin:0;padding:0;display:grid;gap:1px}
.pp-page .pp-toc a{display:flex;gap:8px;padding:4px 10px;border-left:2px solid var(--rule);border-radius:0 6px 6px 0;color:var(--muted);font:400 12.5px/1.4 var(--sans);text-decoration:none}
.pp-page .pp-toc a:hover{color:var(--text);background:var(--row-hover,var(--panel-2))}
.pp-page .pp-toc a[aria-current]{color:var(--text);border-left-color:var(--accent);font-weight:500}
.pp-page .pp-toc .n{flex:none;min-width:1.6em;color:var(--faint);font-family:var(--mono);font-size:11.5px;font-variant-numeric:tabular-nums}
.pp-page .pp-toc a[aria-current] .n{color:var(--muted)}
.pp-page .pp-toc .t{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pp-page .pp-toc-m{display:none;margin:0 0 var(--s-5);padding:var(--s-2) var(--s-3);border:1px solid var(--rule);border-radius:var(--radius-sm,8px)}
.pp-page .pp-toc-m ol{margin:var(--s-2) 0 0;padding-left:1.4em;display:grid;gap:4px;font-size:13.5px}
.pp-page .pp-toc-m a{color:var(--text-2);text-decoration:none}

/* reading type */
.pp-page .pp-article{color:var(--text-2);font:400 16px/1.72 var(--sans);font-feature-settings:"cv11","ss01";hyphens:auto}
.pp-page .pp-article p,.pp-page .pp-article ul,.pp-page .pp-article ol{margin:0 0 1.05em}
.pp-page .pp-article li{margin:.3em 0}
.pp-page .pp-article li::marker{color:var(--faint)}
.pp-page .pp-article strong{color:var(--text);font-weight:600}
.pp-page .pp-article a{color:var(--link);overflow-wrap:anywhere;text-decoration:underline;text-decoration-color:var(--rule-strong);text-underline-offset:3px}
.pp-page .pp-article a:hover{text-decoration-color:var(--link)}
.pp-page .pp-article h2,.pp-page .pp-article h3,.pp-page .pp-article h4{position:relative;color:var(--text);scroll-margin-top:calc(var(--bar-h,var(--gn-bar-h,0px)) + var(--s-4));text-wrap:balance}
.pp-page .pp-article h2{margin:2.6em 0 .7em;padding-top:1.1em;border-top:1px solid var(--rule);font-size:21px;line-height:1.3;letter-spacing:-.01em}
.pp-page .pp-article h3{margin:2em 0 .5em;font-size:16.5px;line-height:1.4}
.pp-page .pp-article h4{margin:0 0 .35em;color:var(--muted);font:600 var(--t-meta)/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase}
.pp-page .pp-article>h2:first-child{margin-top:0;padding-top:0;border-top:0}
.pp-page .pp-article h2#ch0-abstract + p{color:var(--text);font-size:17px;line-height:1.7}
.pp-page .pp-anchor{position:absolute;left:-1.3em;width:1.1em;color:var(--faint);font-weight:400;text-decoration:none!important;opacity:0;transition:opacity .12s ease-out}
.pp-page .pp-article h2:hover .pp-anchor,.pp-page .pp-article h3:hover .pp-anchor,.pp-page .pp-anchor:focus-visible{opacity:1}
.pp-page .pp-anchor:hover{color:var(--accent)}
.pp-page .pp-article code{font:400 .86em var(--mono);color:var(--text);background:var(--panel-2);padding:.08em .32em;border-radius:4px}
.pp-page .pp-article pre{overflow-x:auto;padding:var(--s-3) var(--s-4);background:var(--panel);border:1px solid var(--rule);border-radius:var(--radius-sm,8px)}
.pp-page .pp-article pre code{background:none;padding:0}
.pp-page .pp-article blockquote{margin:0 0 1.05em;padding:0 0 0 var(--s-4);border-left:2px solid var(--rule-strong);color:var(--text)}

/* tables: the system's table type at reading size, wider than the measure where they need it */
.pp-page .pp-article>figure{margin:1.6em 0 1.8em}
.pp-page .pp-article>figure.pp-table{max-width:min(100cqi,1040px)}
.pp-page figure.pp-table>figcaption,.pp-page figure.pp-figure>figcaption{max-width:672px;color:var(--muted);font:400 13px/1.55 var(--sans)}
.pp-page figure.pp-table>figcaption{margin:0 0 var(--s-2)}
.pp-page figure.pp-figure>figcaption{margin:var(--s-3) 0 0}
.pp-page figcaption .pp-cap-n{color:var(--text-2);font-weight:600}
.pp-page .pp-table-wrap{overflow-x:auto;border:1px solid var(--rule);border-radius:var(--radius-sm,8px);background:var(--panel)}
.pp-page .pp-table-wrap table{width:100%;border-collapse:collapse;font:400 13px/1.5 var(--sans);color:var(--text-2);hyphens:manual}
.pp-page .pp-table-wrap th,.pp-page .pp-table-wrap td{padding:8px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}
.pp-page .pp-table-wrap thead th{color:var(--muted);font:600 var(--t-meta)/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase;border-bottom-color:var(--rule-strong);white-space:nowrap}
.pp-page .pp-table-wrap tbody tr:last-child td{border-bottom:0}
.pp-page .pp-table-wrap tbody tr:hover td{background:var(--row-hover,transparent)}
.pp-page .pp-table-wrap td:first-child{color:var(--text)}
.pp-page .pp-table-wrap code{font-size:12px}

/* figures: the paper's diagrams as stacked layers */
.pp-page figure.pp-figure{padding:var(--s-4);border:1px solid var(--rule);border-radius:var(--radius,12px);background:var(--panel)}
.pp-page .layers{display:grid;gap:var(--s-2);margin:0}
.pp-page .layer{padding:var(--s-2) var(--s-3);border:1px solid var(--rule);border-radius:var(--radius-sm,8px);background:var(--bg)}
.pp-page .pp-article .layer p{margin:0;color:var(--text);font:400 14px/1.5 var(--sans)}
.pp-page .arrow{color:var(--faint)}
.pp-page .pp-article .pp-edges{margin-top:var(--s-3)}
.pp-page .pp-article .edges-title{min-height:28px;color:var(--muted);font:500 13px/1.3 var(--sans)}
.pp-page .pp-article .edges{margin:var(--s-1) 0 0;padding-left:1.1em;color:var(--muted);font:400 13px/1.5 var(--sans)}

/* math, written as HTML */
.pp-page .math{font-family:"Cambria Math","STIX Two Math","Times New Roman",serif;white-space:nowrap;color:var(--text)}
.pp-page div.math{display:block;margin:1.2em 0;padding:var(--s-3);text-align:center;font-size:1.1em;overflow-x:auto;background:var(--panel);border-radius:var(--radius-sm,8px)}

@media (max-width:1099px){
  .pp-page .pp-layout{grid-template-columns:minmax(0,1fr)}
  .pp-page .pp-main{grid-column:1}
  .pp-page .pp-toc{display:none}
  .pp-page .pp-toc-m{display:block}
  .pp-page .pp-head,.pp-page .pp-article>*{margin-left:auto;margin-right:auto}
  .pp-page .pp-article>figure.pp-table{max-width:672px}
}
@media (max-width:760px){
  .pp-page .pp-head h1{font-size:21px}
  .pp-page .pp-article{font-size:15.5px}
  .pp-page .pp-article h2{font-size:19px}
  .pp-page .pp-anchor{display:none}
}
@media (prefers-reduced-motion:reduce){.pp-page .pp-anchor{transition:none}}
@media print{.bar,.pp-progress,.pp-toc,.pp-toc-m{display:none}.pp-page .pp-layout{display:block}.pp-page .pp-article{font-size:11pt}}
"""


def enrich(article: str) -> str:
    """The paper's article in the reading frame: each table under its caption in a figure, each
    diagram above its caption in a figure, and a section anchor before each heading's words."""
    def table(m: re.Match) -> str:
        return (f'<figure class="pp-table"><figcaption><span class="pp-cap-n">{m.group(1)}</span>{m.group(2)}</figcaption>'
                f'<div class="pp-table-wrap">{m.group(3)}</div></figure>')
    article = re.sub(r'<p><em>(Table \d+\.)(.*?)</em></p>\n(<table>.*?</table>)', table, article, flags=re.S)
    article = re.sub(r'(?<!<div class="pp-table-wrap">)(<table>.*?</table>)',
                     r'<figure class="pp-table"><div class="pp-table-wrap">\1</div></figure>', article, flags=re.S)

    def links(m: re.Match) -> str:
        count = m.group(1).count("<li>")
        return (f'<details class="gn-disclosure pp-edges"><summary class="edges-title">Links between the layers '
                f'<span class="gn-meta">{count}</span></summary><ul class="edges">{m.group(1)}</ul></details>')
    article = re.sub(r'<p class="edges-title">Links between the layers</p>\n<ul class="edges">(.*?)</ul>', links, article, flags=re.S)
    def figure(m: re.Match) -> str:
        return (f'<figure class="pp-figure">{m.group(1)}<figcaption><span class="pp-cap-n">{m.group(2)}</span>'
                f'{m.group(3)}</figcaption></figure>')
    article = re.sub(r'(<div class="layers">.*?</div>(?:\n<details class="gn-disclosure pp-edges">.*?</details>)?)\n'
                     r'<p><em>(Figure \d+\.)(.*?)</em></p>', figure, article, flags=re.S)
    article = re.sub(r'<(h[23]) id="([^"]+)">',
                     r'<\1 id="\2"><a class="pp-anchor" href="#\2" aria-hidden="true" tabindex="-1">#</a>', article)
    return article


def contents(article: str) -> list[tuple[str, str, str]]:
    """The paper's sections for the contents rail: (anchor, number, words) for each level-two heading."""
    out = []
    for anchor, words in re.findall(r'<h2 id="([^"]+)">(?:<a class="pp-anchor"[^>]*>#</a>)?(.*?)</h2>', article):
        plain = re.sub(r"<[^>]+>", "", words).strip()
        m = re.match(r"(\d+)\.\s+(.*)", plain) or re.match(r"Appendix ([A-Z])\.\s+(.*)", plain)
        out.append((anchor, m.group(1), m.group(2)) if m else (anchor, "", plain))
    return out


def site_page() -> str:
    title, article = body()
    article = enrich(article)
    toc = contents(article)
    words = len(re.sub(r"<[^>]+>", " ", article).split())
    minutes = max(1, round(words / 230 / 5) * 5)
    rail = "".join(f'<li><a href="#{a}" title="{html.escape(t, quote=True)}"><span class="n">{n}</span><span class="t">{t}</span></a></li>'
                   for a, n, t in toc)
    compact = "".join(f'<li><a href="#{a}">{(n + " ") if n else ""}{t}</a></li>' for a, n, t in toc)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta id="nowcast-build" name="nowcast-build" content="{STAMP_TOKEN}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>Who answers for a decision made with AI? · Research paper · InGRID</title>
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#0b1018" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f4f6fa" media="(prefers-color-scheme: light)">
<link rel="stylesheet" href="/grid/{STAMP_TOKEN}/paper.css">
<link rel="stylesheet" href="/grid/{STAMP_TOKEN}/ask.css">
<link rel="stylesheet" href="/grid/{STAMP_TOKEN}/ui.css">
<link rel="stylesheet" href="/grid/{STAMP_TOKEN}/shell.css">
<script src="/grid/{STAMP_TOKEN}/shell.js"></script>
</head>
<body>
<div class="bar"><a class="brand" href="/" aria-label="InGRID home"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 15 8 6l4 6 2-3 3 6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/></svg><span>InGRID</span></a><nav class="sites" aria-label="Sections"><a href="/">Grid</a> <a href="/data">Data</a> <a href="/plants">Plants</a> <a href="/explain">Explain</a> <a href="/outlooks">Outlooks</a> <a href="/paper" aria-current="page">Paper</a> <a href="/models">Models</a> <a href="/work">Work</a> <a href="/map">Map</a> <a href="/alerts">Alerts</a></nav></div>
<section id="ask" data-context="paper" aria-label="Ask Ingrid"></section>
<div class="pp-progress" data-read-progress hidden><span></span></div>
<main class="gn-page pp-page">
<div class="pp-layout">
<nav class="pp-toc" aria-label="Contents" data-toc><p class="gn-label">Contents</p><ol>{rail}</ol></nav>
<div class="pp-main">
<header class="gn-page-head pp-head">
<div class="gn-page-title"><p class="gn-label">Working paper</p><h1>{explainer.inline(title)}</h1></div>
<div class="gn-page-meta"><span class="gn-badge">Draft</span><span class="gn-meta">Working paper, draft of 17 October 2026</span><span class="gn-meta">About {minutes} minutes to read</span></div>
</header>
<details class="pp-toc-m gn-disclosure"><summary>Contents</summary><ol>{compact}</ol></details>
<article class="pp-article" data-read-target>
{article}
</article>
</div>
</div>
</main>
<script src="/grid/{STAMP_TOKEN}/ask.js" defer></script>
<script src="/grid/{STAMP_TOKEN}/reading.js" defer></script>
</body>
</html>
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Exit 1 if the committed page differs from a fresh build")
    args = parser.parse_args(argv)
    outputs = {SITE / "paper.html": site_page(), SITE / "paper.css": CSS}
    if args.check:
        stale = [str(p) for p, t in outputs.items() if (p.read_text(encoding="utf-8") if p.exists() else "") != t]
        if stale:
            print("out of date, run %s to rebuild: %s" % (Path(__file__).name, ", ".join(stale)), file=sys.stderr)
            return 1
        print("the paper page and its stylesheet agree with the Markdown")
        return 0
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path} ({len(text.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
