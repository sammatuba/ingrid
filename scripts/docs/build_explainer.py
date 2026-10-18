"""Build docs/explainer/index.html from the Markdown chapters and the glossary.

Standard library only. The output is deterministic: the same chapters give the same bytes. The page
loads nothing from the network, so it opens from disk. Markers inside the chapters:

    <!-- widget: NAME -->        one interactive element, drawn from WIDGETS below

Outputs: docs/explainer/index.html (one file, opens from disk) and src/grid/explain.html with
explain.css and explain.js, the page the site serves at /explain under its content security policy
(no inline code; the stylesheet and script travel under the build stamp like the grid pages).
    <!-- quiz -->  ...  <!-- /quiz -->   a self-check: "Q: question", options as "- text", "- [x] right"

The two outputs link records differently, because the site serves no Markdown. The single-file copy
links each record where it sits in the repository, and those links work from disk. On the site, each
repository target becomes a reference that shows the record's name and its path in the repository,
so the reader never meets a dead link.

Usage: /usr/bin/python3 scripts/docs/build_explainer.py [--check] [--out PATH]
"""
from __future__ import annotations

import argparse
import html
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAPTERS = ROOT / "docs" / "explainer"
GLOSSARY = ROOT / "docs" / "glossary.md"
OUTPUT = CHAPTERS / "index.html"
SITE = ROOT / "src" / "grid"          # explain.html, explain.css, explain.js: the page the site serves at /explain
STAMP_TOKEN = "__NOWCAST_STAMP__"     # the server writes the build stamp here (src/api/__init__.py)
TITLE = "InGRID, explained"


# ---------------------------------------------------------------- Markdown (the subset the chapters use)

BASE = "docs/explainer"               # every relative target in a chapter or a widget resolves here
SITE_ORIGIN = "https://ingrid-desk.web.app"  # a chapter link to the site itself is a plain path on the site


def repository_target(href: str) -> bool:
    """A target that only resolves against the repository: not a web address, not a fragment,
    not a path from the site's own root. The site serves no Markdown and no source file."""
    return not href.startswith(("http:", "https:", "#", "/", "mailto:"))


def repository_path(href: str) -> str:
    """One target as a path from the repository root, for a reader who holds the repository."""
    return posixpath.normpath(posixpath.join(BASE, href))


def link_html(text: str, href: str, site: bool) -> str:
    """One link. The single-file copy links the record in place. On the site, a repository target
    becomes a reference: the record's name and its path in the repository, never a dead link."""
    if site and href.startswith(SITE_ORIGIN + "/"):
        href = href[len(SITE_ORIGIN):]
    if site and repository_target(href):
        return f'<span class="ref">{text} <code class="ref-path">{html.escape(repository_path(href))}</code></span>'
    return f'<a href="{html.escape(href, quote=True)}">{text}</a>'


def inline(text: str, site: bool = False) -> str:
    """Inline Markdown to HTML: code, bold, italic, links."""
    parts = re.split(r"(`[^`]*`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(f"<code>{html.escape(part[1:-1])}</code>")
            continue
        part = html.escape(part, quote=False)
        part = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: link_html(m.group(1), m.group(2), site), part)
        part = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", part)
        part = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", part)
        out.append(part)
    return "".join(out)


def table(rows: list[str], site: bool = False) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], cells[2:]
    out = ["<table>", "<thead><tr>" + "".join(f"<th>{inline(c, site)}</th>" for c in head) + "</tr></thead>", "<tbody>"]
    for row in body:
        out.append("<tr>" + "".join(f"<td>{inline(c, site)}</td>" for c in row) + "</tr>")
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def quiz(lines: list[str], index: int, site: bool = False) -> str:
    question, options, why = "", [], ""
    for line in lines:
        if line.startswith("Q:"):
            question = line[2:].strip()
        elif line.startswith("Why:"):
            why = line[4:].strip()
        elif re.match(r"^\s*-\s+", line):
            text = re.sub(r"^\s*-\s+", "", line)
            right = text.startswith("[x]")
            options.append((right, text[3:].strip() if right else text))
    out = [f'<div class="quiz" data-quiz="{index}">', f"<p class=\"quiz-q\">{inline(question, site)}</p>", '<div class="quiz-options">']
    for right, text in options:
        out.append(f'<button type="button" class="quiz-opt" data-right="{"1" if right else "0"}">{inline(text, site)}</button>')
    out.append("</div>")
    out.append(f'<p class="quiz-why" hidden>{inline(why, site)}</p>')
    out.append("</div>")
    return "\n".join(out)


def markdown(text: str, widgets: dict[str, str], chapter: int, site: bool = False) -> tuple[str, str, int, int]:
    """Return (html, title, widget_count, quiz_count)."""
    lines = text.splitlines()
    out: list[str] = []
    title = ""
    i = 0
    paragraph: list[str] = []
    widget_count = quiz_count = 0

    def flush():
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph), site)}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        m = re.match(r"^<!--\s*widget:\s*([\w-]+)\s*-->$", stripped)
        if m:
            flush()
            name = m.group(1)
            if name not in widgets:
                raise SystemExit(f"unknown widget {name} in chapter {chapter}")
            out.append(widgets[name])
            widget_count += 1
            i += 1
            continue
        if stripped == "<!-- quiz -->":
            flush()
            block = []
            i += 1
            while i < len(lines) and lines[i].strip() != "<!-- /quiz -->":
                block.append(lines[i])
                i += 1
            quiz_count += 1
            out.append(quiz(block, quiz_count, site))
            i += 1
            continue
        p = re.match(r"^<!--\s*paper:\s*(.+?)\s*-->$", stripped)
        if p:
            flush()
            out.append(paper_box(p.group(1), site))
            i += 1
            continue
        if stripped.startswith("<!--"):
            i += 1
            continue
        if stripped.startswith("```"):
            flush()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(block))}</code></pre>")
            i += 1
            continue
        if not stripped:
            flush()
            i += 1
            continue
        h = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if h:
            flush()
            level = len(h.group(1))
            if level == 1 and not title:
                title = h.group(2)
                i += 1
                continue
            slug = re.sub(r"[^\w\s-]", "", h.group(2).lower()).replace(" ", "-")
            out.append(f'<h{level} id="ch{chapter}-{slug}">{inline(h.group(2), site)}</h{level}>')
            i += 1
            continue
        if stripped.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(table(rows, site))
            continue
        if stripped.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(quote), site)}</p></blockquote>")
            continue
        if re.match(r"^\s*([-*+]|\d+[.)])\s+", line):
            flush()
            ordered = bool(re.match(r"^\s*\d+[.)]\s+", line))
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            # The list's own indentation. A deeper-indented line continues the current item even
            # when it begins like a marker ("  2026. https://..." inside a reference entry); only a
            # line at the list's indentation starts a new item.
            indent = len(line) - len(line.lstrip())
            while i < len(lines) and lines[i].strip():
                current = lines[i]
                current_indent = len(current) - len(current.lstrip())
                item = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$", current)
                if item and current_indent <= indent:
                    items.append(item.group(1))
                elif items and current_indent > indent:
                    items[-1] += " " + current.strip()
                else:
                    break
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x, site)}</li>" for x in items) + f"</{tag}>")
            continue
        paragraph.append(stripped)
        i += 1
    flush()
    return "\n".join(out), title, widget_count, quiz_count


# ---------------------------------------------------------------- glossary tooltips

def glossary_terms(path: Path) -> list[tuple[str, str]]:
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("Word",):
            continue
        word = re.sub(r"\s*\(.*\)$", "", cells[0])
        meaning = re.sub(r"`([^`]*)`", r"\1", cells[1])
        terms.append((word, meaning))
    return terms


def mark_terms(body: str, terms: list[tuple[str, str]]) -> str:
    """Wrap the first occurrence of each glossary term in the prose of one chapter."""
    tokens = re.split(r"(<[^>]+>)", body)
    depth_skip = 0
    seen: set[str] = set()
    patterns = [(w, re.compile(r"(?<![\w-])(" + re.escape(w) + r"s?)(?![\w-])(?!\s+Nowcast)", re.I), m) for w, m in terms]
    for n, token in enumerate(tokens):
        if token.startswith("<"):
            tag = re.match(r"<(/?)(\w+)", token)
            if tag and tag.group(2) in ("code", "a", "h1", "h2", "h3", "h4", "button", "pre", "th", "svg", "text", "label", "option", "summary", "details"):
                depth_skip += -1 if tag.group(1) else 1
            continue
        if depth_skip > 0 or not token.strip():
            continue
        segments: list[tuple[str, bool]] = [(token, True)]  # (text, is_plain)
        for word, pattern, meaning in patterns:
            if word in seen:
                continue
            for k, (segment, plain) in enumerate(segments):
                if not plain:
                    continue
                m = pattern.search(segment)
                if m:
                    seen.add(word)
                    span = f'<span class="term" tabindex="0" data-def="{html.escape(meaning, quote=True)}">{m.group(1)}</span>'
                    segments[k:k + 1] = [(segment[:m.start()], True), (span, False), (segment[m.end():], True)]
                    break
        tokens[n] = "".join(text for text, _ in segments)
    return "".join(tokens)


# ---------------------------------------------------------------- widgets (inline HTML; the page script animates them)

WIDGETS = {
"assumption-chain": """
<div class="widget" data-widget="assumption-chain">
<p class="widget-title">An outlook rests on assumptions. Press the button and watch one break.</p>
<div class="chain">
<div class="card outlook">Outlook: Visayas supply margin for 21 September 2026 is <b>comfortable</b>.</div>
<div class="arrows">rests on</div>
<div class="cards">
<div class="card a" data-a="1">Demand peaks near the usual evening value.</div>
<div class="card a" data-a="2">PEDC Unit 2 supplies 83.7 MW all day.</div>
<div class="card a" data-a="3">Both undersea links run as scheduled.</div>
</div>
</div>
<div class="row"><button type="button" class="btn" data-act="trip">13:34, NGCP: "PEDC Unit 2 tripped"</button>
<button type="button" class="btn ghost" data-act="reset">Reset</button></div>
<p class="widget-note" data-note>Nothing has happened yet.</p>
</div>
""",
"three-grids": """
<div class="widget" data-widget="three-grids">
<p class="widget-title">Three grids, two undersea links. Hover or tap a part.</p>
<svg viewBox="0 0 520 260" class="grids" role="img" aria-label="Luzon, Visayas and Mindanao joined by two links">
<rect class="g" data-info="Luzon. One of the three grids. Site codes 01 to 03 belong here." x="40" y="30" width="200" height="90" rx="10"/>
<text x="140" y="82" text-anchor="middle">Luzon</text>
<rect class="g" data-info="Visayas. The middle grid. PEDC Unit 2, code 08PEDC_U02, is here. Site codes 04 to 08 belong here." x="280" y="100" width="200" height="90" rx="10"/>
<text x="380" y="152" text-anchor="middle">Visayas</text>
<rect class="g" data-info="Mindanao. The southern grid. Site codes 09 to 14 belong here." x="40" y="160" width="200" height="90" rx="10"/>
<text x="140" y="212" text-anchor="middle">Mindanao</text>
<line class="link" data-info="Undersea link Luzon to Visayas (VISLUZ1). Power can flow either way. The market schedules it every five minutes." x1="240" y1="75" x2="280" y2="145"/>
<line class="link" data-info="Undersea link Visayas to Mindanao (MINVIS1). Power can flow either way." x1="240" y1="205" x2="280" y2="145"/>
</svg>
<p class="widget-note" data-note>Each grid has its own demand, price and reserve at every moment.</p>
</div>
""",
"pedc-clock": """
<div class="widget" data-widget="pedc-clock">
<p class="widget-title">21 September 2026 in Visayas. Move the clock.</p>
<input type="range" min="0" max="1439" value="800" step="1" class="clock" aria-label="Time of day">
<div class="row"><span class="time" data-time>13:20</span><span class="state" data-state></span></div>
<ul class="events" data-events>
<li data-at="814">13:34, NGCP notice V133937: PEDC Unit 2 tripped.</li>
<li data-at="818">13:38, notice V135622: the operator drops some load for a short time.</li>
<li data-at="907">15:07, notice V155556: PEDC Unit 2 is back on line.</li>
<li data-at="1020">17:00 to 20:00, notice V141257: yellow alert, the reserve is low.</li>
</ul>
<p class="widget-note">Times and notice numbers come from the case brief. The unit's power during the outage is not in any notice.</p>
</div>
""",
"cutoff-pair": """
<div class="widget" data-widget="cutoff-pair">
<p class="widget-title">The desk judges twice: just before the notice, and just after. Switch the cutoff.</p>
<div class="row seg"><button type="button" class="btn seg-btn active" data-cut="t0">Before, 13:39:36</button><button type="button" class="btn seg-btn" data-cut="t1">After, 13:39:37</button></div>
<div class="passages">
<div class="passage known">Register, February 2026: PEDC Unit 2, maximum 83.7 MW. <small>known since February</small></div>
<div class="passage" data-known="t1">Notice V133937, posted 13:39: PEDC Unit 2 tripped at 13:34. <small>known at 13:39</small></div>
<div class="passage later">Notice V155556, posted 15:55: back on line at 15:07. <small>known at 15:55, outside both cutoffs</small></div>
</div>
<p class="widget-note" data-note>Before the notice, the desk may read only the register. The answer should be: the assumption stands.</p>
</div>
""",
"question-set": """
<div class="widget" data-widget="question-set">
<p class="widget-title">The eight questions, with Gemini's recorded answers on the trip. Tap a question.</p>
<ol class="questions">
<li data-plain="Which unit does the notice talk about? The model named the right one: PEDC Unit 2."><b>Q1 identity</b> <span class="ans">08PEDC_U02</span></li>
<li data-plain="What kind of event is it? A forced outage: the unit stopped without a plan."><b>Q2 event</b> <span class="ans">forced outage</span></li>
<li data-plain="When did it happen, compared with the assumption's day? The same day."><b>Q3 time</b> <span class="ans">same</span></li>
<li data-plain="Is the notice conditional or planned? No. It reports a fact."><b>Q4 conditional</b> <span class="ans">no</span></li>
<li data-plain="Does the notice only repeat an earlier source? No. It is new information."><b>Q5 repeat</b> <span class="ans">no</span></li>
<li data-plain="Does it report something that happened, not a plan? Yes."><b>Q6 observed</b> <span class="ans">yes</span></li>
<li data-plain="Is there enough evidence to decide? Yes."><b>Q7 enough</b> <span class="ans">yes</span></li>
<li data-plain="Taken alone, does the notice support or challenge the assumption? It challenges it."><b>Q8 direction</b> <span class="ans">challenges</span></li>
</ol>
<p class="widget-note" data-note>Each question has a short list of allowed answers. The model cannot answer in free text.</p>
<div class="row"><button type="button" class="btn" data-act="wordings">Show the four forms of Q2 on the trip run</button></div>
<div class="wordings" hidden>
<div class="passage">Form 0, the base text and the options in their base order. <b>forced outage</b></div>
<div class="passage">Form 1, the same options in another order. <b>forced outage</b></div>
<div class="passage">Form 2, each option replaced by a bracketed number. <b>the number for forced outage</b></div>
<div class="passage">Form 3, the passages in reverse order. With one passage, this form equals form 0. <b>forced outage</b></div>
<p class="widget-note">Q2 is a choice question, so no form negates it. The same answer in every form gives a flip rate of 0, stable. Two different answers out of four would give 0.5, above the 0.25 threshold, and the label would become "not enough evidence".</p>
</div>
</div>
""",
"label-rule": """
<div class="widget" data-widget="label-rule">
<p class="widget-title">Code turns the answers into one label. Change an answer and watch the label.</p>
<div class="row wrap">
<label>Q2 event <select data-q="q2"><option value="forced outage" selected>forced outage</option><option value="commercial operation">commercial operation</option><option value="testing">testing</option><option value="other">other</option></select></label>
<label>Q3 time <select data-q="q3"><option value="same" selected>same</option><option value="before">before</option><option value="after">after</option><option value="not stated">not stated</option></select></label>
<label>Q7 enough <select data-q="q7"><option value="yes" selected>yes</option><option value="no">no</option></select></label>
<label>Stable <select data-q="stable"><option value="yes" selected>yes</option><option value="no">no</option></select></label>
</div>
<p class="label-out">Label: <b data-label>challenges</b></p>
<p class="widget-note" data-note>A forced outage on an availability assumption challenges it. The judgment records the rule that fired.</p>
</div>
""",
"practice-decision": """
<div class="widget" data-widget="practice-decision">
<p class="widget-title">Your turn. The AI says "challenges". You decide. Nothing leaves this page.</p>
<div class="card outlook">Assumption: PEDC Unit 2 supplies <b>83.7 MW</b> on 21 September 2026. Judgment at 13:39: <b>challenges</b>, stable.</div>
<form class="decision" data-form>
<div class="row wrap">
<label><input type="radio" name="d" value="keep" checked> Keep the assumption</label>
<label><input type="radio" name="d" value="change"> Change it</label>
<label><input type="radio" name="d" value="open"> Open it for review</label>
</div>
<label class="full">Your reason <input type="text" data-reason placeholder="Example: the unit returned at 15:07, so the day total holds" maxlength="140"></label>
<div class="row"><button type="submit" class="btn">Save the decision</button></div>
</form>
<p class="widget-note" data-note>The desk needs a reason. On the real site the decision goes to your own copy of the case in Firestore.</p>
<ol class="history" data-history><li>00:10, the case starts: the assumption of 83.7 MW comes from the register, and nobody has tested it yet.</li></ol>
</div>
""",
"finding-mechanism": """
<div class="widget" data-widget="finding-mechanism">
<p class="widget-title">Each known risk of model judgment meets one mechanism in the design. Pick a risk.</p>
<div class="row wrap" data-findings>
<button type="button" class="btn ghost" data-f="0">The model's stated confidence is not calibrated</button>
<button type="button" class="btn ghost" data-f="1">Answers change with option order or labels</button>
<button type="button" class="btn ghost" data-f="2">Answers change when a yes/no question flips</button>
<button type="button" class="btn ghost" data-f="3">The model cannot say "I do not know"</button>
<button type="button" class="btn ghost" data-f="4">The model reads past the cutoff</button>
<button type="button" class="btn ghost" data-f="5">The evidence carries instructions</button>
</div>
<div class="detail" data-mech>Pick a risk above.</div>
<p class="widget-note">The mechanisms come from sections 9.3 and 9.5 of the paper. The paper tests sensitivity to presentation, not general robustness.</p>
</div>
""",
"layer-stack": """
<div class="widget" data-widget="layer-stack">
<p class="widget-title">The layers. Click one to see what it owns and what it never grants.</p>
<div class="stack">
<button type="button" class="layer" data-l="0">Versioned sources, series, advisories</button>
<button type="button" class="layer" data-l="1">Access, availability, identity and quantity checks</button>
<button type="button" class="layer" data-l="2">The task compiler: from shared vocabulary and accepted state to one task</button>
<button type="button" class="layer" data-l="3">Models inside the compiled task: the question set</button>
<button type="button" class="layer" data-l="4">Composed label, stability record, escalation</button>
<button type="button" class="layer" data-l="5">Analyst decision, one atomic commit</button>
<button type="button" class="layer" data-l="6">Immutable outlook history and proposal</button>
</div>
<div class="passage" data-info>Click a layer.</div>
<p class="widget-note">From the earlier working paper, section 4.1, and the boundary table of the architecture index.</p>
</div>
""",
"record-axes": """
<div class="widget" data-widget="record-axes">
<p class="widget-title">Every record carries four independent labels. Set them and read the record's meaning.</p>
<div class="row wrap">
<label>Content kind <select data-ax="kind"><option>observation</option><option>reported claim</option><option>interpretation</option><option selected>assumption</option><option>prediction</option><option>scenario input</option><option>simulation output</option><option>review decision</option></select></label>
<label>Review state <select data-ax="review"><option>unreviewed</option><option>proposed</option><option selected>accepted</option><option>retained</option><option>rejected</option><option>deferred</option><option>investigating</option></select></label>
<label>Availability <select data-ax="avail"><option selected>verified by cutoff</option><option>later than cutoff</option><option>unknown</option><option>denied</option></select></label>
<label>Execution mode <select data-ax="mode"><option>live inference</option><option selected>stored run</option><option>retrospective replay</option><option>deterministic</option><option>synthetic test data</option></select></label>
</div>
<div class="passage" data-read></div>
<p class="widget-note">"Accepted" is a review state, not a content kind: it never turns a prediction into an observation. These labels sit in the top box of Figure 4 of the paper.</p>
</div>
""",
"cutoff-slider": """
<div class="widget" data-widget="cutoff-slider">
<p class="widget-title">Move the information cutoff, second by second. The desk admits a passage once the cutoff reaches its known-at time.</p>
<input type="range" min="48000" max="58000" value="49176" step="1" class="clock" aria-label="Cutoff time, seconds since midnight">
<div class="row"><span class="time" data-time>13:39:36</span><span class="state" data-count></span></div>
<div class="passages" data-list>
<div class="passage" data-known="-1" data-kind="register">Registered-capacity list: PEDC unit 2, 83.7 MW. <small>first row on 5 February 2026, known-at taken as the start of that day</small></div>
<div class="passage" data-known="49177" data-kind="notice">V133937: "PEDC U2 Tripped at 1334H". <small>header 13:40, known-at 13:39:37</small></div>
<div class="passage" data-known="50182" data-kind="notice">V135622: manual load dropping at 1338H after the trip. <small>header 13:57, known-at 13:56:22</small></div>
<div class="passage" data-known="51177" data-kind="notice">V141257: Visayas on yellow alert for 1700H to 2000H. <small>header 14:13, known-at 14:12:57</small></div>
<div class="passage" data-known="57356" data-kind="notice">V155556: "PEDC Unit 2 re-online at 1507H". <small>header 15:56, known-at 15:55:56</small></div>
<div class="passage" data-known="unknown" data-kind="dispatch">The unit's real-time schedule: 0.0 MW from 13:45 to 15:15. <small>no recorded availability time: unknown, never admitted</small></div>
</div>
<p class="widget-note" data-note></p>
<p class="widget-note">The slider covers 13:20:00 to 16:06:40, Manila time. The two recorded runs read as of 13:39:37 and 15:55:56, the known-at times of the first and the fourth notice. Paper, appendix C.</p>
</div>
""",
"transaction-race": """
<div class="widget" data-widget="transaction-race">
<p class="widget-title">One decision, one atomic commit. Step through it, with or without a race.</p>
<div class="row seg"><label><input type="checkbox" data-race> Another decision lands on the same copy first</label></div>
<ol class="walk">
<li data-step="1"><b>Prepare.</b> One call returns the case heads, the belief snapshot at the audit cutoff, and the task compiled at the notice's information cutoff.</li>
<li data-step="2"><b>Decide.</b> The analyst chooses retain, revise or investigate and writes a reason. The page binds an idempotency key to the case, the decision and a counter.</li>
<li data-step="3"><b>Commit.</b> The server compares the expected heads with the current heads.</li>
<li data-step="4" data-ok="Heads match: one transaction writes the decision, the new outlook head and the audit entry. A receipt comes back." data-race="Heads differ: the server refuses with STALE_HEAD, 409, and writes nothing. The page says that the case moved since this page loaded, so reload and decide again."></li>
<li data-step="5"><b>Read back.</b> The page reads the accepted outlook and adopts its recorded time as the next audit cutoff. A retry with the same key returns the same receipt.</li>
</ol>
<div class="row"><button type="button" class="btn" data-act="next">Next step</button><button type="button" class="btn ghost" data-act="reset">Start again</button></div>
<p class="widget-note" data-note>The information cutoff stays the notice's. Only the audit cutoff moves.</p>
</div>
""",
"rule-table": """
<div class="widget" data-widget="rule-table">
<p class="widget-title">The whole rule table, in the order the code checks it. Set the answers. The first row that fits is the label.</p>
<div class="row wrap">
<label>Stable <select data-q="stable"><option value="yes" selected>yes</option><option value="no">no</option></select></label>
<label>Q7 enough <select data-q="q7"><option value="yes" selected>yes</option><option value="no">no</option></select></label>
<label>Q1 identity <select data-q="q1"><option value="mapped" selected>the mapped unit</option><option value="other">another unit</option><option value="cannot_tell">cannot tell</option></select></label>
<label>Q2 event <select data-q="q2"><option value="forced_outage" selected>forced outage</option><option value="planned_outage">planned outage</option><option value="derating">derating</option><option value="return_to_service">return to service</option><option value="commercial_operation">commercial operation</option><option value="testing">testing</option><option value="grid_alert">grid alert</option><option value="other">other</option></select></label>
<label>Q3 time <select data-q="q3"><option value="same" selected>same</option><option value="before">before</option><option value="after">after</option><option value="not_stated">not stated</option></select></label>
<label>Q4 conditional <select data-q="q4"><option value="no" selected>no</option><option value="yes">yes</option></select></label>
<label>Q5 repeat <select data-q="q5"><option value="no" selected>no</option><option value="yes">yes</option></select></label>
<label>Q6 observed <select data-q="q6"><option value="yes" selected>yes</option><option value="no">no</option></select></label>
<label>Q8 direction <select data-q="q8"><option value="challenges" selected>challenges</option><option value="supports">supports</option><option value="neither">neither</option></select></label>
<label>The belief is an availability quantity <select data-q="avail"><option value="yes" selected>yes</option><option value="no">no</option></select></label>
</div>
<table class="rules"><thead><tr><th>#</th><th>Row, in the order the code checks it</th><th>Label</th></tr></thead><tbody data-rows>
<tr data-r="0"><td>1</td><td>Any question unstable: a flip rate above 0.25 or a polarity gap above 0.3</td><td>not enough evidence</td></tr>
<tr data-r="1"><td>2</td><td>Q7 modal answer no, below 0.6</td><td>not enough evidence</td></tr>
<tr data-r="2"><td>3</td><td>Q1 cannot tell</td><td>not enough evidence</td></tr>
<tr data-r="3"><td>4</td><td>Q1 is not the mapped unit</td><td>unrelated</td></tr>
<tr data-r="4"><td>5</td><td>Q2 other, or a grid alert that names no unit</td><td>unrelated</td></tr>
<tr data-r="5"><td>6</td><td>Q5 modal answer yes, a repeat of an earlier source</td><td>the earlier source's label, or not enough evidence without one</td></tr>
<tr data-r="6"><td>7</td><td>availability belief, Q2 commercial operation or return to service, Q3 same, Q4 no</td><td>supports</td></tr>
<tr data-r="7"><td>8</td><td>availability belief and Q2 testing</td><td>challenges</td></tr>
<tr data-r="8"><td>9</td><td>availability belief and Q2 planned outage, forced outage or derating, or Q3 after</td><td>challenges</td></tr>
<tr data-r="9"><td>10</td><td>Q3 before and Q6 yes, and Q8 is not challenges</td><td>supports (the contestable row)</td></tr>
<tr data-r="10"><td>11</td><td>Q3 before and Q6 yes, but Q8 challenges</td><td>mixed</td></tr>
<tr data-r="11"><td>12</td><td>Q4 yes and Q3 same or before</td><td>mixed</td></tr>
<tr data-r="12"><td>13</td><td>Q3 not stated</td><td>mixed if Q8 is not neither, else not enough evidence</td></tr>
<tr data-r="13"><td>14</td><td>no row matched</td><td>not enough evidence</td></tr>
</tbody></table>
<p class="label-out">Label: <b data-label>challenges</b> <span class="widget-note" data-fired></span></p>
<p class="widget-note">These are the fourteen rules of appendix C of the paper, in their order. Rows 7 to 9 fire only for an availability belief. The thresholds are initial values, and the team did not tune them.</p>
</div>
""",
"receipt-sim": """
<div class="widget" data-widget="receipt-sim">
<p class="widget-title">The stability record for question 2, the event. Change what each form answered and watch the receipt.</p>
<div class="row wrap">
<label>Form 0, base text <select data-w="0"><option selected>forced outage</option><option>testing</option><option>other</option></select></label>
<label>Form 1, options reordered <select data-w="1"><option selected>forced outage</option><option>testing</option><option>other</option></select></label>
<label>Form 2, options numbered <select data-w="2"><option selected>forced outage</option><option>testing</option><option>other</option></select></label>
<label>Form 3, passages reversed <select data-w="3"><option selected>forced outage</option><option>testing</option><option>other</option></select></label>
</div>
<p class="label-out">Modal answer: <b data-modal>forced outage</b> · flip rate <b data-flip>0.00</b> · <b data-verdict>stable</b></p>
<p class="widget-note" data-note>The flip rate is the share of forms whose top answer differs from the modal one. Strictly above 0.25, the whole judgment counts as unstable and the label becomes "not enough evidence". One differing form out of four is exactly 0.25 and stays stable. Two is 0.5 and does not. Question 2 is a choice question, so no form negates it. Paper, section 9.3.</p>
</div>
""",
"claim-checker": """
<div class="widget" data-widget="claim-checker">
<p class="widget-title">Which of these may the paper say? Click a claim.</p>
<div class="row wrap" data-claims>
<button type="button" class="btn ghost" data-c="0">"The desk warns before the operator does."</button>
<button type="button" class="btn ghost" data-c="1">"Gemini read the PEDC trip as a challenge, stably, on a recorded run."</button>
<button type="button" class="btn ghost" data-c="2">"The judgment score is the probability of a blackout."</button>
<button type="button" class="btn ghost" data-c="3">"The question set beats a single question."</button>
<button type="button" class="btn ghost" data-c="4">"The supply family caused the price spike in case 1."</button>
<button type="button" class="btn ghost" data-c="5">"A kept belief with a reason is a success."</button>
</div>
<div class="detail" data-answer>Click a claim.</div>
<p class="widget-note">Each answer follows the evidence grades and the limits in sections 7, 8 and 14 of the paper.</p>
</div>
""",
"pipeline-layers": """
<div class="widget" data-widget="pipeline-layers">
<p class="widget-title">The data foundation, layer by layer. Click a stage.</p>
<div class="stack">
<button type="button" class="layer" data-l="0">Raw: external tables over the company's WESM files in Cloud Storage</button>
<button type="button" class="layer" data-l="1">Curated: one row per five-minute interval and region, prices, parsed advisories, alert windows</button>
<button type="button" class="layer" data-l="2">Labels and features: reserve condition labels, 17 model inputs, three-hour embargo</button>
<button type="button" class="layer" data-l="3">Models: boosted trees locally, TabFM and TimesFM inside BigQuery, scored out of sample</button>
<button type="button" class="layer" data-l="4">Semantic state: fixed vocabularies per interval and region, alerts as of each interval</button>
<button type="button" class="layer" data-l="5">The replay files the site reads: regions, hvdc, advisories, sites, nodes, events, vectors</button>
</div>
<div class="passage" data-info>Click a stage.</div>
<p class="widget-note">From the data foundation handoff and the grid data build.</p>
</div>
""",
"vector-sum": """
<div class="widget" data-widget="vector-sum">
<p class="widget-title">A history is a sum. Add events and watch the point move.</p>
<svg viewBox="0 0 320 200" class="grids" role="img" aria-label="A path through a plane"><line x1="0" y1="100" x2="320" y2="100" stroke="#2a2f37"/><line x1="160" y1="0" x2="160" y2="200" stroke="#2a2f37"/><g data-plot></g></svg>
<div class="row wrap">
<button type="button" class="btn ghost" data-v="20,-6">planned outage</button>
<button type="button" class="btn ghost" data-v="-18,8">return to service</button>
<button type="button" class="btn ghost" data-v="10,30">trip</button>
<button type="button" class="btn ghost" data-v="24,24">load dropping</button>
<button type="button" class="btn ghost" data-v="-4,-22">link de-blocked</button>
<button type="button" class="btn" data-act="reset">Clear</button>
</div>
<p class="widget-note" data-note>Each event type has one learned vector. The day's state is their running sum, clipped to a maximum length after each step. Below the clip the order does not matter and a linear score splits into one share per event. Once the clip engages, the order matters and the shares are approximate. These vectors are illustrative. The real 175 live in the data build.</p>
</div>
""",
"cache-classes": """
<div class="widget" data-widget="cache-classes">
<p class="widget-title">Every answer carries one of three cache classes. Pick a request.</p>
<div class="row wrap" data-urls>
<button type="button" class="btn ghost" data-u="0">GET /</button>
<button type="button" class="btn ghost" data-u="1">GET /grid/3f9a…c1/grid.js</button>
<button type="button" class="btn ghost" data-u="2">GET /grid-data/3f9a…c1/regions.json</button>
<button type="button" class="btn ghost" data-u="3">GET /grid-data/regions.json</button>
<button type="button" class="btn ghost" data-u="4">POST /demo/session</button>
<button type="button" class="btn ghost" data-u="5">GET /health</button>
</div>
<div class="passage" data-answer>Pick a request.</div>
<p class="widget-note">The stamp is a 64-bit fingerprint over the replay files and the design files, computed once at start. A changed byte changes every versioned URL, so a browser can keep a stamped file for a year.</p>
</div>
""",
"cold-timeline": """
<div class="widget" data-widget="cold-timeline">
<p class="widget-title">What a visitor waits for. Toggle the server's state.</p>
<div class="row seg"><label><input type="checkbox" data-asleep> No server running (cold start)</label></div>
<ol class="walk">
<li data-step="1" data-t="0.1 s" data-ct="0.1 s"><b>The page</b> from Hosting, near the visitor.</li>
<li data-step="2" data-t="0.3 s" data-ct="0.9 s"><b>Seven replay files</b> in parallel from Hosting. The grid draws. Cold: 0.86 s with the server provably cold (run 4).</li>
<li data-step="3" data-t="" data-ct="6.2 s"><b>One warm-up call</b> after the first paint. If no server runs, Google starts one: median 6.2 s over 14 starts read from the Cloud Run log.</li>
<li data-step="4" data-t="1.5 s" data-ct="1.5 s"><b>The first action</b> creates the visitor's own copy in one step.</li>
<li data-step="5" data-t="1.7 s" data-ct="1.7 s"><b>A decision</b>: prepare, commit, read back.</li>
</ol>
<div class="row"><button type="button" class="btn" data-act="next">Next step</button><button type="button" class="btn ghost" data-act="reset">Start again</button><span class="time" data-total>0.0 s so far</span></div>
<p class="widget-note">Numbers from the performance baseline, runs 4, 8 and 10 and the Cloud Run log. Typical values, not promises.</p>
</div>
""",
"request-walk": """
<div class="widget" data-widget="request-walk">
<p class="widget-title">What happens when you open the event page. Step through it.</p>
<div class="row seg"><label><input type="checkbox" data-asleep> No server is running (cold start)</label></div>
<ol class="walk">
<li data-step="1" data-t="0.86 s" data-ct="0.86 s"><b>Firebase Hosting</b> sends the page and the grid files from a location near you. You see the first screen. The measured value is for a cold visit.</li>
<li data-step="2" data-t="" data-ct="6.7 s"><b>Cloud Run</b> receives the first request for your case. If no server is running, Google starts one. With a running server there is no separate wait to show.</li>
<li data-step="3" data-t="1.52 s" data-ct="1.52 s"><b>Sign-in service</b> gives you a private identity. The app server makes your own copy of the case in <b>Firestore</b>, in one step.</li>
<li data-step="4" data-t="1.68 s" data-ct="1.68 s"><b>The decision path.</b> Save a decision. The server checks that your copy did not change under you, writes it, and returns the history.</li>
<li data-step="5" data-t="0 s" data-ct="0 s"><b>No model call.</b> The judgment on the page is the recorded run of 14 October 2026.</li>
</ol>
<div class="row"><button type="button" class="btn" data-act="next">Next step</button><button type="button" class="btn ghost" data-act="reset">Start again</button><span class="time" data-total>0.0 s</span></div>
<p class="widget-note">Times come from the performance baseline: the first screen, the server start, the visitor session and the decision path. They are typical values, not promises.</p>
</div>
""",
"task-life": """
<div class="widget" data-widget="task-life">
<p class="widget-title">The life of one task. Step through it.</p>
<ol class="walk">
<li data-step="1"><b>Idea.</b> A GitHub issue, or a line in a session. Example: "the event page should load in two requests".</li>
<li data-step="2"><b>Task.</b> The coordinator AI registers <code>PERF-3</code>: allowed files, acceptance checks, a verify command.</li>
<li data-step="3"><b>Branch.</b> <code>task/PERF-3</code> in its own work copy. Only the allowed files change.</li>
<li data-step="4"><b>Build.</b> The builder AI, or a person, builds it and writes commands and results into the task record.</li>
<li data-step="5"><b>Checks.</b> The repository check, the plan check and the test suite pass.</li>
<li data-step="6"><b>Review.</b> The reviewer AI, or a person who did not write it, answers accept or rework. Rework goes back to step 4.</li>
<li data-step="7"><b>Accept.</b> The owner records the accept. The state becomes done in two files, in one commit.</li>
<li data-step="8"><b>Merge.</b> The coordinator AI merges into the shared line and pushes. A deploy comes later, once per batch.</li>
</ol>
<div class="row"><button type="button" class="btn" data-act="next">Next step</button><button type="button" class="btn ghost" data-act="reset">Start again</button></div>
<p class="widget-note" data-note>Nobody merges their own work. That is the one rule that always holds.</p>
</div>
""",
"ai-roles": """
<div class="widget" data-widget="ai-roles">
<p class="widget-title">One model, two roles, two settings. The label and the write never pass through the second role.</p>
<div class="roles">
<div class="role">
<h4>System One: the eight typed questions</h4>
<p><b>Thinking off</b>, with a budget of zero. One fixed data shape carries the answers. Every question comes in four presentation forms. The desk reads the order of the top answers and the gaps between them, never a claimed probability.</p>
<p class="role-status">Status: recorded, on the one real case.</p>
</div>
<div class="role">
<h4>System Two: the analysis</h4>
<p><b>Thinking high.</b> It reads cited passages, writes competing interpretations and a review brief, and raises an escalation when the evidence is thin.</p>
<p class="role-status">Status: designed. The transport exists in the code, and no live task has run.</p>
</div>
</div>
<div class="row"><button type="button" class="btn" data-act="example">Show the real PEDC example</button></div>
<div class="passage" data-example hidden>
<p><b>The return cutoff, the real case.</b> Gemini read the four notices as a forced outage, so the label was challenges. The scripted reading gave supports. No analyst has decided yet. The disagreement waits for a person's review.</p>
<p class="widget-note">The desk keeps the disagreement and shows it. The record is the live run of 14 October 2026.</p>
</div>
<p class="widget-note">Neither role accepts an assumption. Acceptance is the analyst's act, and the write stays in code.</p>
</div>
""",
"belief-span": """
<div class="widget" data-widget="belief-span">
<p class="widget-title">A belief with its source and its time span. Press a button and change one of them.</p>
<div class="passages">
<div class="passage known" data-part="belief"><b>The belief.</b> The bridge is open today.</div>
<div class="passage known" data-part="source"><b>The source.</b> A driver's report, this morning.</div>
<div class="passage known" data-part="span"><b>The time span.</b> Today.</div>
</div>
<div class="row"><button type="button" class="btn" data-act="source">Weaken the source</button>
<button type="button" class="btn ghost" data-act="span">Extend the time span</button>
<button type="button" class="btn ghost" data-act="reset">Start again</button></div>
<p class="widget-note" data-note>Nothing has changed yet. A belief holds while its source and its time span hold.</p>
</div>
""",
"decision-line": """
<div class="widget" data-widget="decision-line">
<p class="widget-title">A decision has a line and a cost. Move the cost across the line.</p>
<div class="passages">
<div class="passage known"><b>The line.</b> A change of 1,000,000 PHP is material. Below the line, the change does not count as material.</div>
</div>
<input type="range" min="0" max="2000000" value="400000" step="50000" class="clock" aria-label="The size of the change, in pesos">
<div class="row"><span class="time" data-amount>400,000 PHP</span><span class="state" data-verdict></span></div>
<p class="widget-note" data-note></p>
<p class="widget-note"><b>Synthetic.</b> The line and the arithmetic come from the [[impact-record]], a method demonstration on a made-up portfolio of volumes and contract prices. Every peso figure here is a demonstration, never a business number.</p>
</div>
""",
"loop-stages": """
<div class="widget" data-widget="loop-stages">
<p class="widget-title">The governed loop: knowledge, judgment, work, learning. Press Next and watch one stage light at a time.</p>
<div class="loop">
<div class="stage" data-s="0"><b>Knowledge</b><span>What we know, and why</span></div>
<div class="stage" data-s="1"><b>Judgment</b><span>What we expect, and what we may do</span></div>
<div class="stage" data-s="2"><b>Work</b><span>Who acts, and with what authority</span></div>
<div class="stage" data-s="3"><b>Learning</b><span>What the outcome changes</span></div>
</div>
<div class="passage" data-info>Press Next to start.</div>
<p class="widget-note" data-note>Four stages, one loop. The first three leave records that the next stage reads. The learning stage exists only as a design: nothing reads a score yet.</p>
<div class="row"><button type="button" class="btn" data-act="next">Next stage</button><button type="button" class="btn ghost" data-act="reset">Start again</button></div>
</div>
""",
"miss-cause": """
<div class="widget" data-widget="miss-cause">
<p class="widget-title">A miss has a cause. Pick one to see what changes.</p>
<div class="row wrap" data-causes>
<button type="button" class="btn ghost" data-c="0">The belief was wrong</button>
<button type="button" class="btn ghost" data-c="1">The signal came late</button>
<button type="button" class="btn ghost" data-c="2">The method was wrong</button>
</div>
<div class="passage" data-info>Pick a cause above.</div>
<p class="widget-note">When the desk scores a month, a person can write the cause of a miss as a record of its own beside the score. The record exists. The desk has scored no month yet, so nobody has written a real cause.</p>
</div>
""",
}

# The companion's own widgets (the third part). Three shared kinds keep the script small:
# data-kind="pick" (a button's data-say fills the output), data-kind="switch" (buttons set a value
# per group, and an element with data-when shows only when every condition holds) and
# data-kind="walk" (the step-by-step list the request walk already uses). Every figure comes from
# the paper section the widget's note names.
WIDGETS.update({
"grade-sort": """
<div class="widget" data-widget="grade-sort" data-kind="pick">
<p class="widget-title">Every figure in the paper carries one evidence grade. Pick a claim and read its grade.</p>
<div class="row wrap">
<button type="button" class="btn ghost" data-say="Measured. The authors matched 27 late schedule rows to advisories and measured each lag against the advisory time. Paper, section 7.2.">The schedule shows an outage a median 8.5 hours after the advisory.</button>
<button type="button" class="btn ghost" data-say="Demonstrated. Two real runs with receipts, on one case. No label scored them, so the grade stops short of measured. Paper, section 7.5.">The model gave the same answers in every presentation form on the PEDC trip.</button>
<button type="button" class="btn ghost" data-say="Implemented. Code and tests exist, and the tests use copies of the case. No analyst decision exists on the real case. Paper, table 5.">A decision record binds each decision to one forecast version.</button>
<button type="button" class="btn ghost" data-say="Specified. The paper gives the contract and six rules. Nothing ran. Paper, section 10.">A model arranges a view from a fixed catalogue, and a validator checks it.</button>
<button type="button" class="btn ghost" data-say="Absent. The paper lists it among the numbers the hypothesis needs and that do not exist yet. Paper, table 12.">Out-of-date beliefs cause the costly misses.</button>
<button type="button" class="btn ghost" data-say="Measured, and the answer is no claim. Each series has 27 month origins. No fold reaches the 60 origins that the calibration rule asks for, so no month group can pass. Paper, section 7.3.">The price forecast has skill at the month horizon.</button>
</div>
<div class="detail" data-out>Pick a claim above.</div>
<p class="widget-note">The five grades, strongest first: measured, demonstrated, implemented, specified, absent. Paper, section 7.1.</p>
</div>
""",
"driver-card": """
<div class="widget" data-widget="driver-card" data-kind="switch">
<p class="widget-title">The two worked cases of the driver card. Pick a case and a mode.</p>
<div class="row wrap seg"><button type="button" class="btn seg-btn active" data-set="case:1">Case 1: Visayas, 21 Sep 2026, 13:40</button><button type="button" class="btn seg-btn" data-set="case:2">Case 2: Visayas, 25 Jun 2026, 09:10</button></div>
<div class="row wrap seg"><button type="button" class="btn seg-btn active" data-set="mode:assumed">Assumed</button><button type="button" class="btn seg-btn" data-set="mode:hindsight">Hindsight</button><button type="button" class="btn seg-btn" data-set="mode:strict">Strict</button></div>
<div class="detail" data-when="case:1">Price 29,919 pesos per MWh, band very high. The operator reports "PEDC U2 tripped at 1334H". PEDC unit 2 has a registered capacity of 83.7 MW. No projected schedule holds a row for the trip.</div>
<div class="detail" data-when="case:2">Price 32,000 pesos per MWh, the offer cap. PEDC unit 3, 150 MW, is out in three projected schedules. The desk first saw those rows at 09:40 and 10:00.</div>
<ol class="ranks" data-when="case:1 mode:assumed"><li>Supply 0.777: import share 0.105 against a 28-day median of 0.066.</li><li>Demand 0.771: 2,502 MW against 2,382 MW.</li><li>Fuel 0.473: coal, a cost baseline.</li><li>Outages 0.119: 21 MW scheduled out against 33 MW.</li></ol>
<p class="widget-note" data-when="case:1 mode:assumed">Confidence low: 2 of 41 facts carry evidence of their known-at time, and 39 rest on an assumption (A-RT 30, A-RUN 8, A-FUEL 1). The card withholds 23 facts. Severity high: price band very high, reserves healthy, no alert, top score 0.78.</p>
<p class="detail" data-when="case:1 mode:hindsight">Hindsight admits every fact. For case 1 the ranking stays the same as in the assumed mode.</p>
<p class="detail" data-when="case:1 mode:strict">Strict mode reads only evidenced known-at times. Every family scores "no data", and severity stays unrated. The card shows 2 facts and withholds 61.</p>
<ol class="ranks" data-when="case:2 mode:assumed"><li>Outages 0.854: derated capacity 607 MW against 584 MW.</li><li>Supply 0.577: import share 0.169 against 0.157.</li><li>Demand 0.426.</li><li>Fuel 0.507, after the outage family, because that family scores 0.8 or more.</li></ol>
<p class="widget-note" data-when="case:2 mode:assumed">Confidence medium: 18 of 47 facts carry evidence of their known-at time, and 29 rest on an assumption (A-RT 28, A-FUEL 1). The card withholds 4 facts and lists 1 unconfirmed match. Severity high: price band extreme, reserves healthy, yellow alert, top score 0.85.</p>
<p class="detail" data-when="case:2 mode:hindsight">Outages first at 0.961: the 150 MW outage, against 0 in the reference. At 09:10 the schedule rows for this outage did not exist yet.</p>
<p class="detail" data-when="case:2 mode:strict">The paper does not record the strict card for case 2.</p>
<p class="widget-note">All values come from table 4 of the paper. Each ranking shows the strongest indicator of a family against its 28-day median at the same hour. Fuel compares with its own full history.</p>
</div>
""",
"rank-walk": """
<div class="widget" data-widget="rank-walk" data-kind="walk">
<p class="widget-title">How the card ranks the families, step by step. Press Next.</p>
<ol class="walk">
<li>Pick the region, the time and the mode. The mode decides which facts the card may read.</li>
<li>For demand, supply and outages, read the same region at the same clock hour on each of the 28 days before. The time itself stays out.</li>
<li>Score the indicator: the share of the reference values below it, with ties as one half. A score near 1 means the value was unusually high.</li>
<li>A family with several indicators keeps its strongest. Supply takes the largest of reserve shortfall, import share and congested links.</li>
<li>Fuel compares coal and LNG with their own full history. Fuel is a slow cost level, not an hourly move.</li>
<li>Order the families by score. When a non-fuel family scores 0.8 or more, fuel goes after every scored non-fuel family.</li>
<li>A family with no visible fact says "no data", never zero. The price shows as context, and the card does not score it.</li>
<li>Print the fixed heading: likely drivers, ranked by how unusual each was against the last 28 days at this hour. Evidence, not proof.</li>
</ol>
<div class="row"><button type="button" class="btn" data-act="next">Next</button><button type="button" class="btn ghost" data-act="reset">Start again</button></div>
<p class="widget-note">The steps follow section 3.4 of the paper. A holiday counts like any other day, because no holiday record exists.</p>
</div>
""",
"judgment-walk": """
<div class="widget" data-widget="judgment-walk" data-kind="walk">
<p class="widget-title">The recorded judgment on the PEDC trip, step by step. Press Next.</p>
<ol class="walk">
<li><b>The belief.</b> PEDC unit 2 has 83.7 MW of available capacity. The value comes from the registered-capacity list, whose row for the unit first appears on 5 February 2026.</li>
<li><b>The notice.</b> Advisory V133937: "PEDC U2 Tripped at 1334H (Unplanned Outage)". Its header says 13:40. The market feed logged it at 13:39:37, its known-at time.</li>
<li><b>The cutoff.</b> The run reads as of 13:39:37. One passage qualifies. The unit's real-time schedule has no recorded availability time, so the run leaves it out.</li>
<li><b>The questions.</b> Eight bounded questions, each with a closed list of options: identity, event, time relation, conditional, repeat, observation, sufficiency and direction.</li>
<li><b>The forms.</b> One request carries each question in four presentation forms. With one passage, a yes/no question has two distinct forms and a choice question three.</li>
<li><b>The answers.</b> PEDC unit 2, forced outage, same time, not conditional, not a repeat, an observation, enough evidence, challenges. Every form gave the same top answer.</li>
<li><b>The rules.</b> Rules 1 to 8 do not match. Rule 9 matches: a forced outage on an availability belief challenges it. The label: challenges.</li>
<li><b>The receipt.</b> Model gemini-3.8-flash, thinking budget zero, JSON output. 9,743 tokens in, 1,784 out, 11.1 seconds. The request fingerprint starts 512a7faa6554.</li>
<li><b>The second run.</b> At 15:55:56 the run reads all four advisories, with the full count of forms. The answers stay the same, and rule 9 again gives challenges.</li>
<li><b>The disagreement.</b> A person who reads the latest statement, "re-online at 1507H", answers return to service. Rule 7 then gives supports. The desk keeps both readings.</li>
<li><b>The decision.</b> No analyst has decided on the real case, and the case's test data commits no decision either. The person who reviews the case decides, with a reason.</li>
</ol>
<div class="row"><button type="button" class="btn" data-act="next">Next</button><button type="button" class="btn ghost" data-act="reset">Start again</button></div>
<p class="widget-note">Every value comes from sections 3.6 and 7.5 and appendix C of the paper.</p>
</div>
""",
"forms-count": """
<div class="widget" data-widget="forms-count" data-kind="switch">
<p class="widget-title">The four presentation forms of one question. Pick a run and a question.</p>
<div class="row wrap seg"><button type="button" class="btn seg-btn active" data-set="run:trip">Trip run, one passage</button><button type="button" class="btn seg-btn" data-set="run:return">Return run, four passages</button></div>
<div class="row wrap seg"><button type="button" class="btn seg-btn active" data-set="q:yesno">Q4 conditional, a yes/no question</button><button type="button" class="btn seg-btn" data-set="q:choice">Q2 event, a choice question</button></div>
<ol class="forms" data-when="q:yesno">
<li>Form 0, the base text: "Are the supplied statements conditional, planned or subject to clearance rather than confirmed?"</li>
<li>Form 1, the negated text: "Are the supplied statements unconditional and confirmed?" The desk turns the answer back before it composes.</li>
<li>Form 2: the same as form 0. Bracketed option numbers apply to choice questions only.</li>
<li data-when="run:trip">Form 3: the same as form 0. With one passage, the reversed passage order changes nothing.</li>
<li data-when="run:return">Form 3: form 0 with the four passages in reversed order.</li>
</ol>
<ol class="forms" data-when="q:choice">
<li>Form 0, the base text: "Which event do the supplied passages describe for that entity?" with the eight options in their base order.</li>
<li>Form 1: the same text with the options in another order, fixed by the task's fingerprint.</li>
<li>Form 2: each option label becomes a bracketed number, and the text adds "Answer with one bracketed option identifier."</li>
<li data-when="run:trip">Form 3: the same as form 0. With one passage, the reversed passage order changes nothing.</li>
<li data-when="run:return">Form 3: form 0 with the four passages in reversed order.</li>
</ol>
<p class="label-out" data-when="run:trip q:yesno">Distinct presentations: <b>2</b></p>
<p class="label-out" data-when="run:trip q:choice">Distinct presentations: <b>3</b></p>
<p class="label-out" data-when="run:return q:yesno">Distinct presentations: <b>3</b></p>
<p class="label-out" data-when="run:return q:choice">Distinct presentations: <b>4</b></p>
<p class="widget-note">The forms test option order, option labels, negation and passage order. They do not rephrase the question. Paper, section 9.3 and appendix C.</p>
</div>
""",
"model-cards": """
<div class="widget" data-widget="model-cards" data-kind="pick">
<p class="widget-title">Each framework or model, its role, the theory it answers to and its result. Pick one.</p>
<p class="mgroup">Forecasts: they produce positions</p>
<div class="row wrap">
<button type="button" class="btn ghost" data-say="Persistence, the same hour last week, and the seasonal mean by billing month. Role: the bar that every forecast must clear. Theory: judge a forecast against simple benchmarks under a proper loss. Result: the mean absolute error per region and horizon, in table 10. Grade: measured.">Three price baselines</button>
<button type="button" class="btn ghost" data-say="Ridge regression and histogram boosted trees on fourteen inputs, with fixed settings, in six blocked walk-forward folds with a one-day gap. Result: 28 of 192 groups claim skill, 27 of them at the day horizon. Grade: measured.">Ridge and boosted-tree challengers</button>
</div>
<p class="mgroup">Signals: conditions and event probabilities, never mixed with a judgment score</p>
<div class="row wrap">
<button type="button" class="btn ghost" data-say="A pretrained time-series foundation model, through the warehouse's forecast function, zero shot, on five-minute reserve shortfall. Role: a challenger, not an oracle. Result: AUC 0.69 to 0.78 for onset, below the hour-of-day baseline of 0.85 to 0.89. Grade: measured, negative.">TimesFM 2.5</button>
<button type="button" class="btn ghost" data-say="A pretrained tabular foundation model with 2,000 labelled rows and 17 inputs, and no training step. Result: AUC 0.947 in the Visayas and 0.967 in Mindanao on 744 September origins. It ties with the local model and beats hour-of-day. One run, uncalibrated. Grade: measured.">TabFM</button>
<button type="button" class="btn ghost" data-say="Histogram boosted trees on 17 inputs, 200 rounds, depth 4, in three variants. Result: September test AUC 0.914 and 0.950 on one split. The desk shows the rolling variant in four bands. The three-hour variant flagged 7 of 71 alert days before the operator's notice. Grade: measured.">Local onset classifiers</button>
<button type="button" class="btn ghost" data-say="SQL table functions over typed facts, with no model. Role: list the conditions present at a time and rank them by how unusual each was. Theory: the time contract, and attribution without a cause. Result: two cases checked against hand queries. Grade: demonstrated.">The driver card</button>
</div>
<p class="mgroup">The AI worker and its checks</p>
<div class="row wrap">
<button type="button" class="btn ghost" data-say="gemini-3.8-flash answers eight bounded questions over cited passages, in four presentation forms, as JSON, with a thinking budget of zero. Role: propose which belief a signal touches. Theory: trust in automation, and belief change as a proposal. Result: two runs on one case, both stable, one disagreement. Grade: demonstrated.">Gemini under the question set</button>
<button type="button" class="btn ghost" data-say="Fourteen fixed rules over the modal answers. Role: turn eight answers into one label and a stability receipt, as a clear comparison for the model. Result: on 28 tasks with author-written labels, 22 of 28 for the question set and for a single question. Grade: measured on test data.">The fourteen rules</button>
<button type="button" class="btn ghost" data-say="An open-weights model in an 8-bit file of 9.66 GB, served by llama-server in a container. Role: a hosting option for the judgment role. The worker can change, the record cannot. Result: three identical answers to one request in three runs. Grade: demonstrated on a smoke test only.">Clef-Flash</button>
<button type="button" class="btn ghost" data-say="A language model that chooses parts from a fixed catalogue, under a validator. Role: arrange a view and keep a receipt. Result: none. Grade: specified.">The view planner</button>
</div>
<div class="detail" data-out>Pick a framework or a model.</div>
<p class="widget-note">From table 6 and section 8 of the paper.</p>
</div>
""",
"story-map": """
<div class="widget" data-widget="story-map" data-kind="pick">
<p class="widget-title">Twelve user stories, from one of the operating company's market staff. Pick one to see its verdict and the desk question that serves it.</p>
<div class="row wrap">
<button type="button" class="btn ghost" data-say="Reframe. A situational page with demand, price, flows, reserve and the operator's notices, over a replay of eight days. Desk question Q8: what is happening now. Grade: demonstrated on a replay, with no live feed.">1 Trader: one dashboard</button>
<button type="button" class="btn ghost" data-say="Reframe. The alert record ranks the likely drivers as evidence, and an attribution names an owned belief. Questions Q1, Q6 and Q11. Mandatory parts: the five alert fields and the ranking under its fixed heading. Grade: demonstrated on case 1.">2 Trader: an alert with the driving factor</button>
<button type="button" class="btn ghost" data-say="Adopt. Signal records from operator advisories, linked to the availability beliefs they touch. Questions Q2, Q3, Q4 and Q9. Grade: demonstrated.">3 Trader: outages and constraints</button>
<button type="button" class="btn ghost" data-say="Adopt. An event leads to a belief, a forecast version and an impact. Question Q10. Grade: demonstrated up to the belief. The impact uses a synthetic portfolio, and no customer or contract record exists.">4 Portfolio manager: event to portfolio</button>
<button type="button" class="btn ghost" data-say="Adopt. The five alert fields and the cited AI judgment with its stability receipt. Questions Q1, Q9 and Q11. Grade: demonstrated.">5 Portfolio manager: why an alert fired</button>
<button type="button" class="btn ghost" data-say="Defer the capability and specify its form: the governed generative view of section 10. Grade: specified.">6 Portfolio manager: questions in plain language</button>
<button type="button" class="btn ghost" data-say="Defer. It needs relations that are not records yet. The desk answers insufficient and names the missing record. Grade: absent.">7 Risk analyst: indirect relationships</button>
<button type="button" class="btn ghost" data-say="Adopt. The uncovered volume by node and hour. Question Q10. Grade: demonstrated on synthetic data.">8 Trader: exposed volume</button>
<button type="button" class="btn ghost" data-say="Adopt. The impact record with the materiality line. Question Q10. Grade: demonstrated on synthetic data.">9 Portfolio manager: financial impact</button>
<button type="button" class="btn ghost" data-say="Reframe. The scoring receipt, with a person-written attribution to a belief, a signal or the method. Question Q12. Grade: implemented.">10 Portfolio manager: why profit fell</button>
<button type="button" class="btn ghost" data-say="Defer. A scenario input to the forecast method with a recorded change, not specified further. Grade: absent.">11 Risk analyst: scenarios</button>
<button type="button" class="btn ghost" data-say="Adopt. The record framework itself. Questions Q5 and Q7, plus the receipt of any answer. Grade: implemented for every kind, with no complete real trace yet.">12 Risk manager: trace every alert</button>
</div>
<div class="detail" data-out>Pick a story.</div>
<p class="widget-note">From tables 7 and 8 of the paper. The stories are candidate requirements, not the result of a user study.</p>
</div>
""",
"lag-walk": """
<div class="widget" data-widget="lag-walk" data-kind="walk">
<p class="widget-title">How the authors measured the schedule lag, step by step. Press Next.</p>
<ol class="walk">
<li>Take the 2026 outage schedule: 475 distinct rows for 174 generating resources.</li>
<li>Split them. 148 rows first appear after their outage started. These are the late rows.</li>
<li>Match each late row to an advisory of the same event type and plant, and the same unit where the row names one. The advisory must fall within six hours of the outage start.</li>
<li>27 late rows match. An earlier, looser pass on free-text words found 39 and a median of 20.7 hours.</li>
<li>For the 27, the schedule shows the outage a median 8.5 hours after the advisory, 508 minutes. The 90th percentile is 20.6 days, and no row comes before its advisory.</li>
<li>Count the other way. 1,232 of 1,275 generator advisories, 96.6%, have no schedule row for the plant within six hours. This is a coverage gap, not a delay.</li>
<li>Of the 121 unmatched late rows, 43 belong to plants with no advisory in 2026. The schedule marks 76 of the other 78 as planned outages.</li>
<li>From the outage start instead of the advisory, the late rows appear a median 48 hours later. The PEDC trip has no schedule row at all.</li>
</ol>
<div class="row"><button type="button" class="btn" data-act="next">Next</button><button type="button" class="btn ghost" data-act="reset">Start again</button></div>
<p class="widget-note">From section 7.2 of the paper. These numbers measure lag and coverage. They do not show that any decision lost money.</p>
</div>
""",
"skill-test": """
<div class="widget" data-widget="skill-test" data-kind="switch">
<p class="widget-title">The six rules a forecast group must pass before it claims skill. Pick a group.</p>
<div class="row wrap seg"><button type="button" class="btn seg-btn active" data-set="g:luzon">Luzon, ridge, day</button><button type="button" class="btn seg-btn" data-set="g:mindanao">Mindanao, boosted trees, day</button><button type="button" class="btn seg-btn" data-set="g:month">Visayas, ridge, month</button></div>
<table class="rules"><thead><tr><th>Rule</th><th>Result</th></tr></thead><tbody>
<tr><td>1. Beat the best baseline on mean absolute and root mean squared error</td><td><span data-when="g:luzon">Pass: 1,398.2 against 1,789.2. The claim implies the rest.</span><span data-when="g:mindanao">Fail: 2,318.4 against 2,112.5</span><span data-when="g:month">Not reported in full: the gain on mean absolute error is +172.6</span></td></tr>
<tr><td>2. The 95% interval of the gain excludes zero</td><td><span data-when="g:luzon">Pass: +291.8 to +486.9</span><span data-when="g:mindanao">Fail: −441.4 to +15.7</span><span data-when="g:month">Fail: −205.7 to +527.2</span></td></tr>
<tr><td>3. The gain is positive in two thirds of the folds</td><td><span data-when="g:luzon">Pass: 6 of 6</span><span data-when="g:mindanao">Fail: 3 of 6</span><span data-when="g:month">Not reported: the fold gains change sign</span></td></tr>
<tr><td>4. The band covers 60% to 99% overall, and 55% in two thirds of the folds with 60 origins or more</td><td><span data-when="g:luzon">Pass, implied by the claim</span><span data-when="g:mindanao">Not reported</span><span data-when="g:month">Fail: no month fold holds 60 origins</span></td></tr>
<tr><td>5. The common origins keep 95% of the scored origins</td><td><span data-when="g:luzon">Pass: 1,246 of 1,254</span><span data-when="g:mindanao">Pass: 1,246 of 1,254</span><span data-when="g:month">Not reported</span></td></tr>
<tr><td>6. The group is not on the administered slice</td><td><span data-when="g:luzon">Pass, implied by the claim</span><span data-when="g:mindanao">Pass</span><span data-when="g:month">Pass</span></td></tr>
</tbody></table>
<p class="label-out" data-when="g:luzon">Outcome: <b class="supports">claim</b></p>
<p class="label-out" data-when="g:mindanao">Outcome: <b>the baseline wins</b></p>
<p class="label-out" data-when="g:month">Outcome: <b class="insufficient">no claim under this test</b></p>
<p class="widget-note">From section 7.3 and table 11 of the paper. With 27 origins per series, no month group can pass rule 4, whatever its quality.</p>
</div>
""",
"view-validator": """
<div class="widget" data-widget="view-validator">
<p class="widget-title">A validator for one sample plan. The question: why is the price what it is at 13:40? Change the plan and read the verdict.</p>
<div class="row wrap">
<label><input type="checkbox" data-part="cutoff" checked> The cutoff and the mode</label>
<label><input type="checkbox" data-part="families" checked> One block per family, or "no data"</label>
<label><input type="checkbox" data-part="unconfirmed" checked> Unconfirmed matches, listed and not counted</label>
<label><input type="checkbox" data-part="withheld" checked> Withheld facts, counted by reason</label>
<label><input type="checkbox" data-part="ranking" checked> The ranking under its fixed heading</label>
<label><input type="checkbox" data-part="chart"> A free chart that the model draws</label>
</div>
<label class="full">Connecting text <select data-text><option value="quote" selected>"The ranking puts supply first, at [ranking.supply.score]."</option><option value="none">"Supply leads the ranking."</option><option value="numeral">"Supply leads at 0.78."</option></select></label>
<p class="label-out">Verdict: <b data-verdict>accepted</b></p>
<div class="detail" data-reasons>Every mandatory part is present, every part is in the catalogue, and the text quotes its one number by its field.</div>
<p class="widget-note">This check runs in your browser on a sample plan. No model runs. The mandatory parts are those of question kind Q1 in table 8. The rules are those of section 10, which has the grade specified.</p>
</div>
""",
})

# ---------------------------------------------------------------- the paper companion (third part)

# The working paper the third part accompanies. A chapter names the sections it follows with one
# marker line, <!-- paper: 3.4 3.5 C -->, and the builder draws a box that links each section on
# the paper page (the site's /paper, whose anchors come from the same heading rule as these pages).
PAPER = ROOT / "docs" / "product" / "paper-accountable-ai-decisions-2026-10-17.md"


def paper_sections() -> dict[str, tuple[str, str]]:
    """Section key ("3.4", "4", "C", "Abstract") -> (its title, its anchor on the paper page)."""
    found = {}
    for line in PAPER.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if not m:
            continue
        heading = m.group(1)
        slug = "ch0-" + re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-")
        key = re.match(r"^(?:Appendix\s+([A-Z])\.|(\d+(?:\.\d+)?)\.?\s|(Abstract|References)$)", heading)
        if key:
            name = key.group(1) or key.group(2) or key.group(3)
            title = re.sub(r"^(?:Appendix\s+[A-Z]\.|\d+(?:\.\d+)?\.?)\s*", "", heading)
            found[name] = (title, slug)
    return found


def paper_box(spec: str, site: bool = False) -> str:
    """The "In the paper" box at the top of a companion chapter: one link per section it follows."""
    sections = paper_sections()
    items = []
    for key in spec.split():
        if key not in sections:
            raise SystemExit(f"paper marker names section {key}, which the paper does not have")
        title, slug = sections[key]
        label = (f"Appendix {key}" if len(key) == 1 and key.isalpha() else
                 key if key in ("Abstract", "References") else f"Section {key}")
        text = label if label == title else f"{label}: {html.escape(title, quote=False)}"
        items.append(f"<li>{link_html(text, f'{SITE_ORIGIN}/paper#{slug}', site)}</li>")
    return ('<div class="paper-box" data-paper="' + html.escape(spec, quote=True) + '">'
            '<p class="paper-title">In the paper</p><ul>' + "".join(items) + "</ul></div>")


# The paper's six figures, drawn from the paper's own diagram text, so a figure here cannot drift
# from the figure there. A box is a button: a click lists the arrows into it and out of it. The
# plain-language pages ban a few words the paper uses, so the labels pass through this short list.
FIGURES = {
    "fig-chain": (1, "Figure 1 of the paper: the chain from a signal to a scored decision. Select a box."),
    "fig-prototype": (2, "Figure 2 of the paper: the prototype, from the sources to the hosted desk. Select a box."),
    "fig-layers": (3, "Figure 3 of the paper: four layers of responsibility. Select a box."),
    "fig-records": (4, "Figure 4 of the paper: the seven record kinds and how they link. Select a box."),
    "fig-loop": (5, "Figure 5 of the paper: scoring and attribution, the single and the double loop. Select a box."),
    "fig-views": (6, "Figure 6 of the paper: a governed generative view, from the question to the receipt. Select a box."),
}
FIGURE_WORDS = [("Judgment runs recorded with receipts; the public site replays them and makes no live call",
                 "Recorded judgment runs with receipts. The site replays them, with no live call"),
                ("; ", ", "), ("proposes a revision of", "proposes a change to"),
                ("Reviewed belief revision", "Reviewed change to the belief"),
                ("epistemology and belief revision", "epistemology and belief change"),
                ("Manifest of what exists", "List of what exists"), ("digests", "fingerprints"),
                ("digest", "fingerprint")]


def plain_figure_text(text: str) -> str:
    for old, new in FIGURE_WORDS:
        text = text.replace(old, new)
    return text


def paper_diagrams() -> list[list[str]]:
    """The paper's diagram blocks, in order: the first is Figure 1."""
    text = PAPER.read_text(encoding="utf-8")
    return [block.splitlines() for block in re.findall(r"```mermaid\n(.*?)\n```", text, flags=re.S)]


def parse_diagram(lines: list[str]) -> tuple[list[tuple[str, list[str]]], dict[str, str], list[tuple[str, str, str]]]:
    """(groups as (title, node keys), node key -> label, edges as (from, to, note))."""
    labels: dict[str, str] = {}
    groups: list[tuple[str, list[str]]] = []
    edges: list[tuple[str, str, str]] = []
    current: list[str] | None = None
    node = re.compile(r"(\w+)\[([^\]]+)\]")
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("flowchart"):
            continue
        m = re.match(r"subgraph\s+\w+\[([^\]]+)\]", line)
        if m:
            current = []
            groups.append((plain_figure_text(m.group(1)), current))
            continue
        if line == "end":
            current = None
            continue
        for key, label in node.findall(line):
            if key not in labels:
                labels[key] = plain_figure_text(label)
                if current is not None:
                    current.append(key)
        plain = node.sub(r"\1", line)
        chain = re.split(r"\s*-->\s*", plain)
        for left, right in zip(chain, chain[1:]):
            note = ""
            n = re.match(r"\|([^|]+)\|\s*(\w+)", right)
            if n:
                note, right = plain_figure_text(n.group(1)), n.group(2)
            edges.append((left.strip(), right.strip(), note))
    return groups, labels, edges


def figure_widget(name: str) -> str:
    """One figure: a box per node, grouped as in the paper, and the arrows listed once in words. A
    click on a box lights the arrows into it and out of it; the script reads them from that list."""
    number, title = FIGURES[name]
    groups, labels, edges = parse_diagram(paper_diagrams()[number - 1])
    out = [f'<div class="widget" data-widget="{name}" data-kind="figure">',
           f'<p class="widget-title">{html.escape(title, quote=False)}</p>', '<div class="fgroups">']
    for group, keys in groups:
        out.append(f'<div class="fgroup"><h4>{html.escape(group, quote=False)}</h4><div class="nodes">')
        out.extend(f'<button type="button" class="fnode" data-id="{key}">{html.escape(labels[key], quote=False)}</button>'
                   for key in keys)
        out.append("</div></div>")
    out.append("</div>")
    out.append('<div class="detail" data-detail>Select a box. This panel lists the arrows into it and out of it.</div>')
    out.append(f'<details class="fedges"><summary>All {len(edges)} arrows, in words</summary><ol>')
    for left, right, note in edges:
        tail = f". The arrow: {html.escape(note, quote=False)}." if note else "."
        # A box's name up to its colon keeps each arrow one short sentence; the box keeps the full label.
        short = {key: labels[key].split(":")[0] for key in (left, right)}
        out.append(f'<li data-a="{left}" data-b="{right}">{html.escape(short[left], quote=False)} → '
                   f'{html.escape(short[right], quote=False)}{tail}</li>')
    out.append("</ol></details>")
    out.append(f'<p class="widget-note">The boxes and arrows come from the diagram text of the paper\'s Figure {number}.'
               " A few words follow the plain-language list of these pages.</p>")
    out.append("</div>")
    return "\n".join(out)


# ---------------------------------------------------------------- the systems map (DOC-4)

# The nodes, their status words, their numbers and their source records come from the systems
# inventory record docs/work/docs-for-people/systems-inventory-2026-10-15.md. Change that record
# first, then this table. tests/test_explainer.py reads the record and refuses a node whose status
# word differs from it, or a source link whose target is not in the repository.

STATUS_WORDS = ("live", "built", "recorded", "designed")
INVENTORY = "../work/docs-for-people/systems-inventory-2026-10-15.md"
LIVE_RUN = "../work/grid-desk/live-run-2026-10-14.md"

BANDS = [
    ("code", "Code authority",
     "Typed meaning, the compile, the composition, the stability record and the write. Plain code, and every step stays inspectable."),
    ("reading", "The reading side",
     "The port that carries one request shape, the two Gemini roles, and the comparison that measures the method."),
    ("numbers", "The numbers side",
     "The market files become features and labels, and the models score them. The join to the reading side has a contract and no running code path."),
    ("pages", "The event map and the pages",
     "The day as a path, the two pages people open, where the site runs, and the pages that explain all of it."),
]

NODES = [
    dict(id="ontology", name="Shared vocabulary profile v1", band="code", status="built",
         status_note="In the code and the suite.",
         what="Typed meaning: claims, sources, assumptions, mappings and five time fields on every record.",
         role="It fixes what a task may mean before any model sees anything.",
         numbers="Five time fields on every record, and one shared vocabulary for the desk.",
         numbers_source=("the shared vocabulary profile", "../architecture/ontology-profile-v1.md"),
         source=("the shared vocabulary profile", "../architecture/ontology-profile-v1.md")),
    dict(id="compiler", name="Known-then compiler", band="code", status="live",
         status_note="It runs on the site today.",
         what="Filters by access, availability, reviewed identity and context. One fingerprint per task.",
         role="It keeps the future out of every judgment and makes a run repeatable.",
         numbers="Six inputs, four filters in a fixed order, one fingerprint per task.",
         numbers_source=("the working paper, section 5.1", "../product/working-paper-2026-10-11.md"),
         source=("the review core", "../../src/review/README.md")),
    dict(id="transaction", name="Review transaction", band="code", status="live",
         status_note="It runs on the site today.",
         what="A Firestore append with expected heads, a safe-to-repeat key and an audit entry.",
         role="The only path that changes an accepted assumption.",
         numbers="One atomic write per decision. Four refusal codes reach the visitor.",
         numbers_source=("decision system v1, sections 6 and 7", "../architecture/decision-system-v1.md"),
         source=("the decision system", "../architecture/decision-system-v1.md")),
    dict(id="systemone", name="System One API port", band="reading", status="built",
         status_note="Built, and exercised with one backend.",
         what="One request shape: the state plus typed questions, with choice or probability answers.",
         role="It lets any decision backend sit behind one port.",
         numbers="One request shape, with eight questions in four presentation forms per task.",
         numbers_source=("the working paper, section 5.5", "../product/working-paper-2026-10-11.md"),
         source=("the System One adapters", "../../src/adapters/systemone/")),
    dict(id="gemini-s1", name="Decision questions on Gemini", band="reading", status="recorded",
         status_note="Recorded on the one real case.",
         what="Gemini 3.8 Flash on Vertex, one fixed data shape, thinking off, four presentation forms per question.",
         role="It answers the eight typed questions on the recorded run.",
         numbers="8 questions in 4 presentation forms, 9,743 tokens in on the trip cutoff, and every flip rate zero.",
         numbers_source=("the live run record, 14 October 2026", "../work/grid-desk/live-run-2026-10-14.md"),
         source=("the Gemini adapters", "../../src/adapters/gemini/"),
         real_case="pedc-u2-2026-09-21"),
    dict(id="compose", name="Composition table", band="code", status="live",
         status_note="It runs on the site today.",
         what="Fourteen rules in a fixed order. The thresholds 0.6, 0.5 and 0.5 were fixed before testing.",
         role="It turns the answers into one label. Code decides, never the model.",
         numbers="14 rules checked in order, and 5 labels plus the fall-through.",
         numbers_source=("the judgment code, version 5", "../../src/judgment/bundle.py"),
         source=("the working paper, section 5.3", "../product/working-paper-2026-10-11.md")),
    dict(id="receipt", name="Stability record", band="code", status="built",
         status_note="Built, and never fired: every flip rate was zero.",
         what="Flip rate and polarity gap across the four presentation forms. An unstable answer set falls back to not enough evidence.",
         role="It turns the audit findings of 2026 into a mechanism on the page.",
         numbers="Unstable above a flip rate of 0.25. Every recorded rate was 0.",
         numbers_source=("the comparison report", "../work/probe-bundle/evaluation.md"),
         source=("the working paper, section 5.3", "../product/working-paper-2026-10-11.md")),
    dict(id="gemini-s2", name="Gemini analysis (System Two)", band="reading", status="designed",
         status_note="The transport exists in the code. No live task has run.",
         what="Cited claim extraction, competing interpretations, a review brief and an escalation path.",
         role="The analysis layer. It never composes the label and never accepts an assumption.",
         numbers="Thinking high, and four jobs named. No live task yet.",
         numbers_source=("the working paper, section 5.7", "../product/working-paper-2026-10-11.md"),
         source=("research 26, section 8", "../research/26-google-stack-fit.md")),
    dict(id="bigquery", name="BigQuery data foundation", band="numbers", status="built",
         status_note="The teammate's work.",
         what="Five-minute WESM tables. Features as known at the time, labels matured, with a three-hour gap.",
         role="The source of every figure on the grid page.",
         numbers="292,839 rows to 29 September 2026, 253 parsed advisories and 28 model inputs per row.",
         numbers_source=("the data foundation handoff", "../work/data-foundation/intent.md"),
         source=("the data and event map chapter", "21-data-and-event-map.md")),
    dict(id="timesfm", name="TimesFM through AI.FORECAST", band="numbers", status="recorded",
         status_note="Recorded: an onset AUC of 0.69 to 0.78, below the hour-of-day baseline. The what-if runs nowhere yet.",
         what="A Google time-series model inside BigQuery, at version 2.5 GA and 3.0 preview.",
         role="The reserve-shortfall forecast, and the covariate what-if for scenarios.",
         numbers="Onset AUC 0.69 to 0.78, below the hour-of-day baseline, from one recorded run.",
         numbers_source=("the TimesFM and TabFM record", "../work/data-foundation/timesfm-tabfm.md"),
         source=("the TimesFM and TabFM record", "../work/data-foundation/timesfm-tabfm.md")),
    dict(id="tabfm", name="TabFM through AI.PREDICT", band="numbers", status="recorded",
         status_note="Recorded, from one comparison.",
         what="A zero-shot tabular model inside BigQuery, at preview.",
         role="A reserve-onset classifier from 17 grid features.",
         numbers="AUC 0.943 in Visayas and 0.961 in Mindanao.",
         numbers_source=("the TimesFM and TabFM record", "../work/data-foundation/timesfm-tabfm.md"),
         source=("the TimesFM and TabFM record", "../work/data-foundation/timesfm-tabfm.md")),
    dict(id="boosted", name="Local boosted trees", band="numbers", status="recorded",
         status_note="Recorded, from one comparison.",
         what="Gradient boosting, trained on the same features.",
         role="The baseline that TabFM tied with.",
         numbers="AUC 0.947 and 0.967, a statistical tie with TabFM.",
         numbers_source=("the training record", "../work/data-foundation/training.md"),
         source=("the training record", "../work/data-foundation/training.md")),
    dict(id="event2vec", name="Event2Vec event map", band="pages", status="live",
         status_note="The panel runs on the site today. The numbers below come from the recorded early-warning result.",
         what="One vector per typed operator event. A day is a clipped running sum. 175 types, 16 numbers each.",
         role="The day-as-a-path panel, the nearest similar days and an early-warning probe.",
         numbers="175 event types with 16 numbers each. Noon AUC 0.785 against the best rule 0.717.",
         numbers_source=("the spike record", "../work/event-map/spike-2026-10-15.md"),
         source=("the explore record", "../work/explore/implementation.md")),
    dict(id="grid-page", name="Replay grid page", band="pages", status="live",
         status_note="It runs on the site today.",
         what="A static desk over the five-minute data files. Every element is explorable.",
         role="How people meet the data.",
         numbers="Seven replay files, under one stamp.",
         numbers_source=("the explore record", "../work/explore/implementation.md"),
         source=("the grid chapter", "02-grid.md")),
    dict(id="event-page", name="Event page", band="pages", status="live",
         status_note="It runs on the site today.",
         what="The recorded judgment, the cutoff pair, the rule that fired and the decision form.",
         role="How people meet the judgment.",
         numbers="8 answers, their rule and their stability record, on one page.",
         numbers_source=("the grid desk record", "../work/grid-desk/implementation.md"),
         source=("the grid desk record", "../work/grid-desk/implementation.md")),
    dict(id="evaluation", name="Evaluation harness", band="reading", status="recorded",
         status_note="22 of the 28 agree both ways. The question set abstains 4 times.",
         what="28 labelled compiles and three ablations, with the measures fixed before any backend ran.",
         role="The evidence for the method, and for the claims the project refuses.",
         numbers="28 labelled compiles, 22 both ways, 4 abstentions, one of them right.",
         numbers_source=("the comparison report", "../work/probe-bundle/evaluation.md"),
         source=("the comparison report", "../work/probe-bundle/evaluation.md")),
    dict(id="hosting", name="Cloud Run and Firebase Hosting", band="pages", status="live",
         status_note="It runs on the site today.",
         what="Stamped files from the CDN, and an app server that starts on the first request.",
         role="Where the site runs.",
         numbers="One server at most, and one deploy per batch of finished work.",
         numbers_source=("the hosting record", "../work/hosting/implementation.md"),
         source=("the hosting chapter", "22-hosting-in-depth.md")),
    dict(id="docs", name="Plain-language pages and explainer", band="pages", status="live",
         status_note="It runs on the site today.",
         what="Checked pages for people, and these interactive chapters at /explain.",
         role="How the team and the judges understand the project.",
         numbers="{chapters} chapters in three parts, and every number names its record.",
         numbers_source=("the DOC record", "../work/docs-for-people/implementation.md"),
         source=("this explainer's index", "README.md")),
]

NODE_BY_ID = {node["id"]: node for node in NODES}

# The flows between the nodes, in the order the reader follows them. Each step is a node (or two
# nodes side by side) or an anchor for an event that is not a component. The arrow after a step
# carries its caption.
FLOWS = [
    dict(id="reading", title="The reading side: one notice, judged.",
         note="Seven arrows, from the notice to the write. Every step here sits on the event page.",
         steps=[
             dict(anchor="A notice arrives", title="An operator notice, with the minute it became known.",
                  arrow="The desk draws one task at the notice's cutoff."),
             dict(node="compiler", arrow="One request shape carries the typed questions."),
             dict(node="systemone", arrow="The model answers the eight questions in four presentation forms."),
             dict(node="gemini-s1", arrow="Code turns the top answers into one label."),
             dict(node="compose", arrow="The stability record says whether the forms agreed."),
             dict(node="receipt", arrow="The analyst decides, and gives a reason."),
             dict(anchor="The analyst decides", title="The one act the desk reserves for a person.",
                  arrow="One atomic write records the decision, or refuses it."),
             dict(node="transaction"),
         ]),
    dict(id="numbers", title="The numbers side: the market files to the figures.",
         note="Two arrows. The models score the features, and the page draws the figures from the same files.",
         steps=[
             dict(node="bigquery", arrow="The 28 inputs per row feed the models."),
             dict(nodes=("tabfm", "boosted"), arrow="The same data build draws the figures on the page."),
             dict(node="grid-page"),
         ]),
    dict(id="bridge", title="The bridge: a reviewed assumption to a scenario.",
         note="Two arrows. The bridge runs nowhere yet, so the consequence stays uncomputed today.",
         steps=[
             dict(node="transaction",
                  arrow="The reviewed mapping turns an accepted assumption into a future covariate path."),
             dict(node="timesfm", arrow="Two forecasts with two paths give a directional difference."),
             dict(anchor="The what-if answer", title="Designed and not run. It would be labelled directional."),
         ]),
]

# The parts of the path, in reading order. Each chapter file belongs to exactly one part, and the
# same titles label the navigation tiers.
PARTS = [
    ("The ideas", "The four questions behind the desk, in plain words, and the system that carries them.",
     ("00-ideas-1-know.md", "00-ideas-2-do.md", "00-ideas-3-who.md", "00-ideas-4-learn.md", "00-system.md")),
    ("The desk", "One layer per chapter, in plain words: the problem, the grid, evidence, the judgment, the site and the work.",
     ("01-why.md", "02-grid.md", "03-evidence.md", "04-judgment.md", "05-runs.md", "06-work.md")),
    ("The paper, step by step",
     "A companion to the working paper, in its order. Each chapter names its sections, walks the method on the real cases and ends with a self-check.",
     ("07-paper-guide.md", "08-time-contract.md", "09-signal-to-decision.md", "10-driver-card.md",
      "11-judgment-showcase.md", "12-compiler-and-transaction.md", "13-rules-and-receipt.md",
      "14-methods-and-models.md", "15-requirements.md", "16-measurements.md", "17-layers-and-records.md",
      "18-generated-views.md", "19-grounding.md", "20-evaluation-and-honesty.md", "21-data-and-event-map.md",
      "22-hosting-in-depth.md")),
]

# One line per chapter and the components it brings into the story. The path widget prints the line
# and the names; the chapter strip highlights the same components, so the one mapping drives both.
CHAPTER_ADD = {
    # DOC-5: the ideas chapters light the records that instantiate each concept, so the strips start
    # from zero on Ideas 1 and the map chapter (last of the tier) arrives with most of them in the
    # story. The mapping follows the theoretical foundation page, section 4 (concept to record).
    "00-ideas-1-know.md": dict(adds=("ontology", "compiler", "bigquery"),
                               line="The first question: what we know, why we believe it, and what a belief rests on."),
    "00-ideas-2-do.md": dict(adds=("compose", "receipt", "systemone", "timesfm", "transaction", "evaluation"),
                             line="The second question: what we do with uncertainty, and what a change is worth."),
    "00-ideas-3-who.md": dict(adds=("gemini-s1", "gemini-s2", "event-page"),
                              line="The third question: who may propose, who may accept, and what the record keeps."),
    "00-ideas-4-learn.md": dict(adds=("boosted",),
                                line="The fourth question: how a settled month changes beliefs, methods and goals."),
    "00-system.md": dict(adds=("event2vec", "grid-page", "hosting", "docs"),
                         line="The whole system in one chapter: the figures, the systems map, the path and the two Gemini roles."),
    "01-why.md": dict(adds=("gemini-s1", "compose"),
                      line="Why a review desk exists at all, and the four things it does for the analyst."),
    "02-grid.md": dict(adds=("grid-page", "event-page"),
                       line="The three grids, the operator and the market, and the day that the site replays."),
    "03-evidence.md": dict(adds=("ontology", "compiler"),
                           line="Evidence with a clock, an assumption with a source, and the cutoff that keeps the future out."),
    "04-judgment.md": dict(adds=("gemini-s1", "systemone", "receipt", "transaction"),
                           line="The eight fixed questions, the four presentation forms, the label and the analyst's decision."),
    "05-runs.md": dict(adds=("hosting", "event-page", "grid-page"),
                       line="One visit to the site, step by step, and every Google piece that it touches."),
    "06-work.md": dict(adds=("docs",),
                       line="The people and the AI helpers, and the life of one task from idea to merge."),
    "07-paper-guide.md": dict(adds=("evaluation",),
                              line="How to read the paper with this companion: the question, the hypothesis and the five evidence grades."),
    "08-time-contract.md": dict(adds=("ontology", "compiler"),
                                line="The six time fields, the three assumptions behind known-at, and the cutoff over the four real notices."),
    "09-signal-to-decision.md": dict(adds=("transaction", "receipt"),
                                     line="The chain from a signal to a scored decision, the materiality line, and attribution as built and as proposed."),
    "10-driver-card.md": dict(adds=("bigquery", "event-page"),
                              line="Showcase: the driver card on two worked cases in three modes, the ranking step by step and the alert."),
    "11-judgment-showcase.md": dict(adds=("gemini-s1", "systemone"),
                                    line="Showcase: the recorded judgment on the PEDC trip, step by step, and the presentation forms counted."),
    "12-compiler-and-transaction.md": dict(adds=("compiler", "transaction"),
                                           line="The compiler's six inputs and the atomic commit that refuses an out-of-date head."),
    "13-rules-and-receipt.md": dict(adds=("systemone", "compose", "receipt"),
                                    line="The typed questions, the whole rule table in its order, and the stability record."),
    "14-methods-and-models.md": dict(adds=("timesfm", "tabfm", "boosted", "gemini-s1"),
                                     line="TimesFM, TabFM, the classifiers, the baselines and Gemini: what each does and the theory it answers to."),
    "15-requirements.md": dict(adds=("grid-page", "event-page"),
                               line="Twelve user stories become twelve desk questions with mandatory parts, and the watch list of 44 factors."),
    "16-measurements.md": dict(adds=("bigquery", "evaluation"),
                               line="The schedule lag step by step, and the six-rule skill test on the price forecast."),
    "17-layers-and-records.md": dict(adds=("ontology", "transaction"),
                                     line="Four layers of responsibility, seven record kinds, and the labels and limits on every record."),
    "18-generated-views.md": dict(adds=("event-page", "receipt"),
                                  line="Governed generative views: the model arranges, the records fill, and a validator checks every plan."),
    "19-grounding.md": dict(adds=("receipt", "compiler"),
                            line="The theories behind the design, and the mechanism that answers each known risk of model judgment."),
    "20-evaluation-and-honesty.md": dict(adds=("evaluation", "gemini-s1"),
                                         line="The null results, the experiments that could refute the design, and the claims the paper refuses."),
    "21-data-and-event-map.md": dict(adds=("bigquery", "tabfm", "timesfm", "boosted", "event2vec", "grid-page"),
                                     line="Behind the prototype: the market files to features and figures, and the day as a path."),
    "22-hosting-in-depth.md": dict(adds=("hosting",),
                                   line="Behind the prototype: the build stamp, the three cache classes, the staged draw and the visitor's own copy."),
}


def _counts() -> dict[str, int]:
    return {word: sum(1 for node in NODES if node["status"] == word) for word in STATUS_WORDS}


def _fill(text: str, files: list[Path]) -> str:
    """Resolve the build-time placeholders, so no count in the node data is typed by hand."""
    return text.format(chapters=len(files), nodes=len(NODES))


def record_attrs(href: str, site: bool) -> tuple[str, str]:
    """The target a detail panel follows, and the repository path shown in its place on the site.
    The site serves no Markdown, so there the target is empty and the detail shows the path."""
    return ("", repository_path(href)) if site and repository_target(href) else (href, "")


def node_button(node: dict, files: list[Path], site: bool = False) -> str:
    """One node: in a band or as a step of a flow. A click fills the detail panel from these fields."""
    label, href = node["source"]
    numbers_label, numbers_href = node["numbers_source"]
    href, source_ref = record_attrs(href, site)
    numbers_href, numbers_ref = record_attrs(numbers_href, site)
    attrs = (f'data-node="{node["id"]}" data-name="{html.escape(node["name"], quote=True)}" '
             f'data-status="{node["status"]}" data-what="{html.escape(_fill(node["what"], files), quote=True)}" '
             f'data-role="{html.escape(_fill(node["role"], files), quote=True)}" '
             f'data-status-note="{html.escape(node["status_note"], quote=True)}" '
             f'data-numbers="{html.escape(_fill(node["numbers"], files), quote=True)}" '
             f'data-numbers-source-label="{html.escape(numbers_label, quote=True)}" '
             f'data-numbers-source-href="{html.escape(numbers_href, quote=True)}" '
             f'data-numbers-source-ref="{html.escape(numbers_ref, quote=True)}" '
             f'data-source-label="{html.escape(label, quote=True)}" data-source-href="{html.escape(href, quote=True)}" '
             f'data-source-ref="{html.escape(source_ref, quote=True)}"')
    return (f'<button type="button" class="node" {attrs}>{html.escape(node["name"])}'
            f'<span class="nst">{node["status"]}</span></button>')


def hero_widget(files: list[Path], site: bool = False) -> str:
    """The opening figures, counted from the node data when the page is built. Nothing here is typed."""
    counts = _counts()
    cases = {node["real_case"] for node in NODES if node.get("real_case")}
    rows = [(word, counts[word], f"components {word}", "status words from the systems inventory", INVENTORY)
            for word in STATUS_WORDS]
    rows.append(("chapters", len(files), "chapters in three parts", "the chapter files in this folder", ""))
    rows.append(("cases", len(cases), "real case", "the live run record of 14 October 2026", LIVE_RUN))
    figures = []
    for key, value, label, note, href in rows:
        small = link_html(note, href, site) if href else note
        figures.append(f'<div class="fig"><b data-hero="{key}">{value}</b><span>{label}</span><small>{small}</small></div>')
    return ("<div class=\"widget\" data-widget=\"hero-figures\">\n"
            "<p class=\"widget-title\">The desk today, in six figures.</p>\n"
            f'<div class="figs">{"".join(figures)}</div>\n'
            "<p class=\"widget-note\">Every figure comes from the node data behind the systems map, at build time. "
            "The four status words are the four of the systems inventory record.</p>\n</div>")


def systems_map_widget(files: list[Path], site: bool = False) -> str:
    """Every component of the inventory as a node, in four bands, with the flows drawn between them."""
    counts = _counts()
    out = ['<div class="widget" data-widget="systems-map">',
           '<p class="widget-title">Every component in place, in four bands. Select a node. Filter by the status word.</p>',
           '<div class="row wrap" data-filters>',
           f'<button type="button" class="btn ghost seg-btn active" data-filter="all" aria-pressed="true">All {len(NODES)}</button>']
    for word in STATUS_WORDS:
        out.append(f'<button type="button" class="btn ghost seg-btn" data-filter="{word}" aria-pressed="false">'
                   f'{word} {counts[word]}</button>')
    out.append("</div>")
    out.append('<div class="map">')
    for band_id, band_title, band_note in BANDS:
        out.append(f'<div class="band" data-band="{band_id}"><h4>{html.escape(band_title, quote=False)}</h4>'
                   f'<p class="band-note">{html.escape(band_note, quote=False)}</p><div class="nodes">')
        for node in NODES:
            if node["band"] == band_id:
                out.append(node_button(node, files, site))
        out.append("</div></div>")
    out.append("</div>")
    out.append('<div class="detail" data-detail>Select a node for what it is, its role, its status word, '
               'its numbers and the source record behind it.</div>')
    arrows = 0
    out.append('<div class="flows">')
    for flow in FLOWS:
        out.append(f'<div class="flow" data-flow="{flow["id"]}"><p class="flow-title">{html.escape(flow["title"], quote=False)}</p>'
                   '<div class="steps">')
        for step in flow["steps"]:
            if "anchor" in step:
                out.append(f'<span class="anchor" title="{html.escape(step["title"], quote=True)}">'
                           f'{html.escape(step["anchor"], quote=False)}</span>')
            elif "nodes" in step:
                for node_id in step["nodes"]:
                    out.append(node_button(NODE_BY_ID[node_id], files, site))
            else:
                out.append(node_button(NODE_BY_ID[step["node"]], files, site))
            if "arrow" in step:
                arrows += 1
                out.append(f'<span class="arrow" data-edge="{arrows}" title="{html.escape(step["arrow"], quote=True)}">→</span>')
        out.append(f'</div><p class="flow-note">{html.escape(flow["note"], quote=False)}</p></div>')
    out.append("</div>")
    out.append('<div class="row"><button type="button" class="btn" data-act="next-arrow">Follow the flow</button>'
               '<button type="button" class="btn ghost" data-act="reset-arrows">Start again</button></div>')
    out.append(f'<p class="widget-note" data-arrow-note>{arrows} arrows in order, across the three flows. '
               'Follow them to see how one notice becomes one decision, and how the numbers side stays apart.</p>')
    out.append('<p class="widget-note">The four status words: live runs on the site today. Built sits in the code and the suite. '
               'Recorded ran once, and its numbers are on record. Designed has a contract and no running code path. '
               'Every node, word and number follows the systems inventory record.</p>')
    out.append("</div>")
    return "\n".join(out)


def path_widget(files: list[Path]) -> str:
    """The chapter list in parts, one line each, with a done marker kept in the reader's own browser."""
    titles = chapter_titles(files)
    out = ['<div class="widget" data-widget="path">',
           f'<p class="widget-title">{len(files)} chapters in three parts. Each line says what the chapter adds '
           'and the components it covers.</p>',
           '<div class="path">']
    position = {path.name: n for n, path in enumerate(files, start=1)}
    for part_title, part_note, part_files in PARTS:
        out.append(f'<div class="part"><h4>{html.escape(part_title, quote=False)}</h4><p class="part-note">{html.escape(part_note, quote=False)}</p>')
        for name in part_files:
            adds = CHAPTER_ADD[name]["adds"]
            chips = "".join(f'<span class="chip">{html.escape(NODE_BY_ID[node_id]["name"])}</span>' for node_id in adds)
            out.append(f'<div class="prow"><button type="button" class="p-done" data-done="{name}" aria-pressed="false" '
                       f'title="Mark this chapter done">Done</button>'
                       f'<button type="button" class="p-go" data-goto="{position[name]}">'
                       f'<span class="n">{position[name]}</span>{html.escape(titles[name])}</button>'
                       f'<p class="p-line">{html.escape(CHAPTER_ADD[name]["line"], quote=False)}</p>'
                       f'<p class="p-chips">{chips}</p></div>')
        out.append("</div>")
    out.append("</div>")
    out.append('<p class="widget-note" data-path-note>No chapter carries a done mark yet.</p>')
    out.append('<p class="widget-note">A done mark lives in your browser only. It is not part of the case, and it never leaves this page.</p>')
    out.append("</div>")
    return "\n".join(out)


def chapter_titles(files: list[Path]) -> dict[str, str]:
    titles = {}
    for path in files:
        first = next((line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("# ")), "")
        if not first:
            raise SystemExit(f"{path.name}: first line must be a level-one heading")
        titles[path.name] = first[2:].strip()
    return titles


def chapter_strip(files: list[Path], n: int) -> str:
    """The systems map in miniature at the top of one chapter: the components this chapter adds,
    and the ones the earlier chapters already brought into the story. The same mapping drives it."""
    name = files[n - 1].name
    add = list(CHAPTER_ADD[name]["adds"])
    before = {node_id for path in files[:n - 1] for node_id in CHAPTER_ADD[path.name]["adds"]}
    names = [NODE_BY_ID[node_id]["name"] for node_id in add]
    listed = " and ".join([", ".join(names[:-1]), names[-1]]) if len(names) > 1 else names[0]
    dots = []
    for band_id, _title, _note in BANDS:
        for node in NODES:
            if node["band"] != band_id:
                continue
            cls = "sdot on" if node["id"] in add else "sdot past" if node["id"] in before else "sdot"
            dots.append(f'<i class="{cls}"></i>')
    shown = len(set(add) | before)
    return (f'<div class="strip" data-widget="chapter-strip" data-strip="ch-{n}" data-adds="{",".join(sorted(add))}">'
            f'<p class="strip-note">This chapter adds <b>{html.escape(listed)}</b>. '
            f'{shown} of {len(NODES)} components are in the story by now.</p>'
            f'<div class="strip-dots" role="img" aria-label="The systems map in miniature">{"".join(dots)}</div></div>')


# The one record a hand-written widget names: the impact record behind the decision widget's line
# and the synthetic peso figure. It follows the same rule as a chapter's links: a reference that
# shows the record's path on the site, a working link in the copy that opens from disk.
WIDGET_REFS = {"[[impact-record]]": ("IMPACT-1 record", "../work/price-outlook/impact.md")}


def widget_refs(markup: str, site: bool = False) -> str:
    """Resolve the record markers in a hand-written widget for the output being built."""
    for marker, (text, href) in WIDGET_REFS.items():
        markup = markup.replace(marker, link_html(text, href, site))
    return markup


def generated_widgets(files: list[Path], site: bool = False) -> dict[str, str]:
    """The three widgets that are built from the data above: the figures, the map and the path."""
    widgets = {"hero-figures": hero_widget(files, site), "systems-map": systems_map_widget(files, site),
               "path": path_widget(files)}
    widgets.update({name: figure_widget(name) for name in FIGURES})
    return widgets


CSS = """
/* InGRID, explained: built by scripts/docs/build_explainer.py, do not edit by hand.
   Platform polish (PP-B4): one stylesheet for the served page and the copy that opens from disk.
   Every rule but the base is scoped under .ex at build time (scope_css), so nothing here reaches
   the site's bar, menus or command bar. The palette below is the copy-from-disk fallback; on the
   site, shell.css sets the live tokens for both themes. Inter and Plex only. */
:root{--bg:#0b1018;--text:#e8edf5;--fg:#e8edf5;--text-2:#b8c4d6;--muted:#8794aa;--faint:#66748a;--rule:#212d40;--line:#212d40;--rule-strong:#2f3f58;--panel:#111824;--card:#111824;--panel-2:#172131;--accent:#7cc4ff;--on-accent:#0b1018;--ok:#3ccf8e;--bad:#ff6b6b;--warn:#f2b134;--link:#a6d4ff;--row-hover:rgba(255,255,255,.035);--sans:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:Plex,ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media (prefers-color-scheme: light){:root{--bg:#f4f6fa;--text:#0f172a;--fg:#0f172a;--text-2:#334155;--muted:#5b6b82;--faint:#8794a8;--rule:#e0e6ef;--line:#e0e6ef;--rule-strong:#c9d2df;--panel:#ffffff;--card:#ffffff;--panel-2:#eef2f8;--accent:#2563eb;--on-accent:#ffffff;--ok:#15803d;--bad:#dc2626;--warn:#b45309;--link:#1d4ed8;--row-hover:rgba(15,23,42,.035)}}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion: reduce){html{scroll-behavior:auto}}
html,body{margin:0;background:var(--bg);color:var(--text)}
body{font:400 13px/1.5 var(--sans);-webkit-font-smoothing:antialiased}
[hidden]{display:none !important}

/* ---------- the frame: the page head, then the chapter rail beside the chapter ---------- */
.ex{display:block;width:100%;max-width:1200px;margin:0 auto;padding:24px 16px 112px}
.ex-head{display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"title actions" "meta meta";align-items:end;gap:8px 16px;margin-bottom:24px}
.ex-title{grid-area:title;min-width:0}
.ex-eyebrow{display:block;margin:0 0 6px;color:var(--muted);font:600 11px/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase}
.ex-head h1{margin:0;color:var(--text);font:600 22px/1.25 var(--sans);letter-spacing:-.01em}
.ex-sub{margin:4px 0 0;max-width:76ch;color:var(--text-2);font-size:14px;line-height:1.5}
.ex-actions{grid-area:actions;display:flex;align-items:center;gap:8px}
.ex-meta{grid-area:meta;display:flex;flex-wrap:wrap;gap:4px 16px;margin:0;color:var(--faint);font-size:12px;line-height:1.5}
.ex-meta p{margin:0}
.ex-view{display:inline-flex;height:28px;border:1px solid var(--rule-strong);border-radius:8px;overflow:hidden}
.ex-view button{margin:0;padding:0 10px;border:0;border-left:1px solid var(--rule);background:transparent;color:var(--muted);font:500 12px/1 var(--sans);cursor:pointer;white-space:nowrap}
.ex-view button:first-child{border-left:0}
.ex-view button:hover{color:var(--text);background:var(--row-hover)}
.ex-view button[aria-pressed="true"]{background:var(--panel-2);color:var(--text);font-weight:600}
.ex-view button:focus-visible{outline:2px solid var(--accent);outline-offset:-2px;border-radius:6px}

.ex-head,.ex-layout{max-width:1040px;margin-left:auto;margin-right:auto}
.ex-layout{display:grid;grid-template-columns:240px minmax(0,1fr);gap:40px;align-items:start}
.ex-rail{position:sticky;top:calc(var(--bar-h,var(--gn-bar-h,0px)) + 16px);max-height:calc(100vh - var(--bar-h,var(--gn-bar-h,0px)) - 32px);overflow-y:auto;overscroll-behavior:contain;padding-bottom:16px;scrollbar-width:thin}
.ex-progress{display:grid;gap:6px;margin:0 0 14px;padding:0 10px 0 12px}
.ex-progress-label{color:var(--muted);font:600 11px/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase}
.progress{height:2px;border-radius:2px;background:var(--rule)}
.progress div{height:100%;border-radius:2px;background:var(--accent);width:0;transition:width .2s ease-out}
.ex-rail ol{list-style:none;margin:0;padding:0;display:grid;gap:1px}
.ex-rail li.tier{margin:14px 0 4px;padding:0 12px;color:var(--faint);font:600 11px/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase}
.ex-rail li.tier:first-child{margin-top:0}
.ex-rail button{all:unset;box-sizing:border-box;display:flex;gap:8px;width:100%;padding:5px 10px;border-left:2px solid var(--rule);border-radius:0 6px 6px 0;color:var(--muted);font:400 13px/1.4 var(--sans);cursor:pointer}
.ex-rail button:hover{color:var(--text);background:var(--row-hover)}
.ex-rail button.active{color:var(--text);border-left-color:var(--accent);font-weight:500}
.ex-rail button:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.ex-rail .n{flex:none;min-width:1.7em;color:var(--faint);font:400 11.5px/1.75 var(--mono);font-variant-numeric:tabular-nums}
.ex-rail button.active .n{color:var(--muted)}

/* ---------- the chapter: reading type ---------- */
.ex-main{min-width:0;max-width:760px;color:var(--text-2);font:400 16px/1.7 var(--sans)}
.ex-main a{color:var(--link);text-decoration:underline;text-decoration-color:var(--rule-strong);text-underline-offset:3px}
.ex-main a:hover{text-decoration-color:var(--link)}
.ex-main p,.ex-main ul,.ex-main ol{margin:0 0 1em}
.ex-main strong{color:var(--text);font-weight:600}
.chapter{display:none;scroll-margin-top:calc(var(--bar-h,var(--gn-bar-h,0px)) + 16px)}
.chapter.active{display:block}
.ex.all .chapter{display:block;border-bottom:1px solid var(--rule);padding-bottom:32px;margin-bottom:40px}
.chapter>p,.chapter>ul,.chapter>ol,.chapter>blockquote{max-width:68ch}
.chapter h2{margin:1.9em 0 .55em;color:var(--text);font:600 19px/1.35 var(--sans);letter-spacing:-.005em;text-wrap:balance;scroll-margin-top:calc(var(--bar-h,var(--gn-bar-h,0px)) + 16px)}
.chapter>.kicker+h2{margin:.2em 0 .75em;font-size:26px;line-height:1.25;letter-spacing:-.015em}
.chapter h3{margin:1.6em 0 .5em;color:var(--text);font:600 16px/1.4 var(--sans)}
.kicker{margin:0;color:var(--muted);font:600 11px/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase}
code{font:400 .86em var(--mono);color:var(--text);background:var(--panel-2);border-radius:4px;padding:.08em .32em}
pre{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:12px;overflow:auto}
pre code{border:0;padding:0;background:none}
table{border-collapse:collapse;width:100%;margin:12px 0 20px;font:400 13.5px/1.5 var(--sans)}
.chapter table{display:block;overflow-x:auto;max-width:100%;border:1px solid var(--rule);border-radius:8px;background:var(--panel)}
.chapter table thead,.chapter table tbody{display:table;width:100%}
th,td{border-bottom:1px solid var(--rule);padding:8px 12px;text-align:left;vertical-align:top}
th{color:var(--muted);font:600 11px/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase}
.chapter table tbody tr:last-child td{border-bottom:0}
blockquote{margin:12px 0;padding:2px 0 2px 16px;border-left:2px solid var(--rule-strong);color:var(--text)}
.term{border-bottom:1px dotted var(--rule-strong);cursor:help;position:relative}
.term:hover,.term:focus{border-bottom-color:var(--accent)}
.term:hover::after,.term:focus::after{content:attr(data-def);position:absolute;left:0;top:1.6em;z-index:9;background:var(--panel);color:var(--text);border:1px solid var(--rule-strong);border-radius:10px;padding:8px 10px;width:min(320px,80vw);font:400 13px/1.45 var(--sans);box-shadow:0 8px 24px rgba(0,0,0,.25)}

/* ---------- widgets: the system's controls and cards ---------- */
.widget{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:16px;margin:20px 0;font-size:14.5px;line-height:1.6}
.widget-title{margin:0 0 10px;color:var(--text);font-weight:600}
.widget-note{color:var(--muted);font-size:13.5px;margin:10px 0 0}
.row{display:flex;gap:8px;align-items:center;margin:12px 0 0}
.row.wrap{flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;min-height:32px;padding:6px 12px;border:1px solid var(--rule-strong);border-radius:8px;background:var(--panel);color:var(--text);font:500 13px/1.3 var(--sans);cursor:pointer;max-width:100%;white-space:normal;text-align:left}
.btn:hover:not([disabled]){background:var(--panel-2);border-color:var(--muted)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent);font-weight:600}
.btn.primary:hover:not([disabled]){background:var(--accent);border-color:var(--accent);filter:brightness(1.06)}
.btn.ghost{background:transparent;color:var(--text-2)}
.btn[disabled]{opacity:.45;cursor:default}
.btn:focus-visible,.seg-btn:focus-visible,.quiz-opt:focus-visible,.node:focus-visible,.fnode:focus-visible,.layer:focus-visible,.p-done:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.seg .seg-btn{background:transparent;color:var(--muted);border:1px solid var(--rule-strong)}
.seg .seg-btn.active{background:var(--panel-2);color:var(--text);border-color:var(--rule-strong);font-weight:600}
.card{border:1px solid var(--rule);border-radius:10px;padding:10px 12px;background:var(--bg)}
.card.outlook{border-color:var(--rule-strong)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.card.a.broken{border-color:var(--bad);color:var(--bad);text-decoration:line-through}
.card.a.found{border-color:var(--bad);box-shadow:0 0 0 1px var(--bad) inset}
.arrows{color:var(--muted);text-align:center;margin:6px 0;font-size:.85rem}
.grids{width:100%;max-width:520px;display:block;margin:0 auto}
.grids .g{fill:var(--bg);stroke:var(--rule-strong);stroke-width:2;cursor:pointer}
.grids .g:hover,.grids .g.active{stroke:var(--accent)}
.grids text{fill:var(--text);font-size:18px;pointer-events:none}
.grids .link{stroke:var(--accent);stroke-width:4;stroke-dasharray:8 6;cursor:pointer}
.grids .link:hover,.grids .link.active{stroke-width:7}
.clock{width:100%;accent-color:var(--accent)}
.time{font:600 1.25rem/1.3 var(--mono);font-variant-numeric:tabular-nums;color:var(--text)}
.state{color:var(--muted)}
.state.bad{color:var(--bad)}
.state.ok{color:var(--ok)}
.state.warn{color:var(--warn)}
.events{list-style:none;padding:0;margin:8px 0 0}
.events li{padding:6px 10px;border-left:2px solid var(--rule);margin:4px 0;color:var(--muted)}
.events li.past{border-color:var(--rule-strong);color:var(--text)}
.events li.now{border-color:var(--bad);color:var(--text);font-weight:600}
.passages{display:grid;gap:8px;margin-top:10px}
.passage{border:1px solid var(--rule);border-radius:8px;padding:8px 10px;opacity:.45}
.passage.known{opacity:1;border-color:var(--ok)}
.passage small{display:block;color:var(--muted)}
.passage.later{opacity:.35}
.questions{padding-left:1.4em;margin:0}
.questions li{padding:6px 8px;border-radius:6px;cursor:pointer}
.questions li:hover{background:var(--row-hover)}
.questions .ans{float:right;color:var(--text);font-family:var(--mono)}
.label-out{font-size:1.15rem;color:var(--text)}
.label-out b{color:var(--text)}
.label-out b.supports{color:var(--ok)}
.label-out b.insufficient{color:var(--muted)}
.label-out b.challenges{color:var(--bad)}
.decision label{display:inline-flex;gap:6px;align-items:center}
.decision .full{display:block;margin-top:10px}
.decision input[type=text]{width:100%;margin-top:4px;padding:8px 10px;border:1px solid var(--rule-strong);border-radius:8px;background:var(--bg);color:var(--text);font:inherit}
.decision input[type=text]:focus{outline:none;border-color:var(--accent)}
.history{margin:10px 0 0;padding-left:1.3em}
.history li{color:var(--muted)}
.history li.new{color:var(--text);font-weight:600}
.walk{padding-left:1.4em}
.walk li{opacity:.4;margin:6px 0;transition:opacity .2s}
.walk li.on{opacity:1}
.walk li.now{opacity:1;color:var(--text);font-weight:600}
.walk li .t{float:right;color:var(--muted);font-family:var(--mono);font-variant-numeric:tabular-nums}
.quiz{border:1px dashed var(--rule-strong);border-radius:12px;padding:14px 16px;margin:20px 0;font-size:14.5px}
.quiz-q{margin:0 0 10px;color:var(--text);font-weight:600}
.quiz-q::before{content:"Check yourself: ";color:var(--muted);font-weight:500}
.quiz-options{display:flex;flex-wrap:wrap;gap:8px}
.quiz-opt{background:var(--panel);color:var(--text);border:1px solid var(--rule-strong);border-radius:8px;padding:6px 12px;font:inherit;cursor:pointer}
.quiz-opt:hover{background:var(--panel-2)}
.quiz-opt.right{border-color:var(--ok);color:var(--ok)}
.quiz-opt.wrong{border-color:var(--bad);color:var(--bad)}
.quiz-why{color:var(--muted);margin:10px 0 0}
.stack{display:flex;flex-direction:column;gap:6px}
.layer{text-align:left;background:var(--bg);color:var(--text);border:1px solid var(--rule);border-radius:8px;padding:8px 12px;font:inherit;cursor:pointer}
.layer:hover,.layer.active{border-color:var(--accent)}
.btn.ghost.active{border-color:var(--accent);color:var(--text)}
.rules{font-size:.88rem;margin-top:10px}
.rules tr.fired td{background:var(--panel-2);color:var(--text)}
.pager{display:flex;justify-content:space-between;gap:10px;margin:32px 0 16px;padding-top:16px;border-top:1px solid var(--rule)}
/* DOC-4: the opening figures, the systems map, the path, the chapter strip and the two roles */
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}
.fig{background:var(--bg);border:1px solid var(--rule);border-radius:10px;padding:10px 12px;min-width:0}
.fig b{display:block;font:500 1.55rem/1.2 var(--mono);color:var(--text);font-variant-numeric:tabular-nums}
.fig span{display:block}
.fig small{display:block;color:var(--muted);margin-top:4px}
.map{display:grid;gap:10px}
.band{border:1px solid var(--rule);border-radius:10px;padding:10px 12px;background:var(--bg);min-width:0}
.band h4,.flow-title,.part h4,.role h4{margin:0 0 4px;color:var(--text);font-size:.95rem}
.band-note,.flow-note,.part-note{color:var(--muted);font-size:.9rem;margin:0 0 8px}
.nodes,.steps{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.node{text-align:left;background:var(--panel);color:var(--text);border:1px solid var(--rule);border-radius:8px;padding:6px 10px;font:inherit;font-size:.92rem;cursor:pointer;max-width:100%;white-space:normal}
.node:hover,.node.active{border-color:var(--accent)}
.node.dim{opacity:.25}
.node .nst{display:inline-block;margin-left:6px;color:var(--muted);font-size:.76rem}
.node.active .nst{color:var(--text-2)}
.flows{display:grid;gap:10px;margin-top:12px}
.flow{border:1px dashed var(--rule-strong);border-radius:10px;padding:10px 12px;min-width:0}
.arrow{border:1px solid transparent;border-radius:6px;padding:1px 4px;color:var(--muted)}
.arrow.on{color:var(--text)}
.arrow.now{background:var(--accent);color:var(--on-accent)}
.anchor{border:1px dashed var(--rule-strong);border-radius:8px;padding:6px 10px;color:var(--muted);font-size:.9rem}
.detail{background:var(--bg);border:1px solid var(--rule);border-radius:10px;padding:10px 12px;margin:12px 0 0;font-size:.95rem}
.detail p{margin:0 0 6px}
.detail p:last-child{margin:0}
.d-name{margin:0 0 6px}
.st{font-style:normal;border:1px solid var(--rule-strong);border-radius:999px;padding:1px 8px;font-size:.78rem;white-space:nowrap}
.st-live{border-color:var(--ok);color:var(--ok)}
.st-recorded{border-color:var(--rule-strong);color:var(--text)}
.st-designed{border-style:dashed;color:var(--muted)}
.strip{display:flex;flex-wrap:wrap;gap:10px;align-items:center;border:1px solid var(--rule);border-radius:10px;background:var(--panel);padding:8px 12px;margin:0 0 20px;font-size:13.5px;line-height:1.5}
.strip-note{margin:0;color:var(--muted);flex:1 1 200px;min-width:0}
.strip-dots{display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.sdot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--rule-strong)}
.sdot.past{background:var(--muted)}
.sdot.on{background:var(--accent)}
.path{display:grid;gap:10px}
.part{border:1px solid var(--rule);border-radius:10px;padding:10px 12px;background:var(--bg);min-width:0}
.prow{display:grid;grid-template-columns:auto 1fr;gap:2px 8px;padding:8px 0;border-top:1px solid var(--rule)}
.prow:first-of-type{border-top:0}
.prow>*{grid-column:2;min-width:0}
.prow>.p-done{grid-column:1;grid-row:1 / span 3}
.p-done{background:transparent;color:var(--muted);border:1px solid var(--rule-strong);border-radius:999px;padding:2px 8px;font:inherit;font-size:.78rem;cursor:pointer;align-self:start}
.p-done.on{border-color:var(--ok);color:var(--ok)}
.p-go{all:unset;cursor:pointer;display:block;color:var(--text);padding:2px 0}
.p-go:hover{color:var(--accent)}
.p-go .n{display:inline-block;width:1.6em;color:var(--faint);font-family:var(--mono)}
.p-go.active{color:var(--text);font-weight:600}
.p-go:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
.p-line{margin:0;color:var(--muted);font-size:.9rem}
.p-chips{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0 0}
.chip{border:1px solid var(--rule-strong);border-radius:999px;padding:1px 8px;font-size:.78rem;color:var(--muted)}
.roles{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.role{border:1px solid var(--rule);border-radius:10px;padding:10px 12px;background:var(--bg);min-width:0}
.role p{margin:0 0 6px}
.role p:last-child{margin:0}
.role-status{color:var(--muted);font-size:.9rem}
/* DOC-4 rework: on the site a repository target is a reference, not a link */
.ref{white-space:normal}
.ref-path{font:400 .86em var(--mono);color:var(--muted);word-break:break-all}
.fig small .ref-path{display:block;margin-top:2px}
.ref-note{margin:0;color:var(--faint);font-size:12px}
/* DOC-5: the loop, the belief, the decision and the miss */
.loop{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin:0 0 10px}
.stage{border:1px dashed var(--rule-strong);border-radius:10px;padding:8px 10px;background:var(--bg);min-width:0;color:var(--muted)}
.stage b{display:block}
.stage span{font-size:.85rem}
.stage.on{border-style:solid;border-color:var(--rule-strong);color:var(--text)}
.stage.now{border-color:var(--accent)}
/* the companion: the paper box, the figures, the ranks and the forms */
.paper-box{border:1px solid var(--rule);border-radius:10px;padding:10px 14px;margin:0 0 20px;background:var(--panel);font-size:14px;line-height:1.55}
.paper-title{margin:0 0 4px;color:var(--muted);font:600 11px/1.3 var(--sans);text-transform:uppercase;letter-spacing:.06em}
.paper-box ul{margin:0;padding-left:1.2em}
.fgroups{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.fgroup{border:1px solid var(--rule);border-radius:10px;padding:8px 10px;background:var(--bg);min-width:0}
.fgroup h4{margin:0 0 6px;font-size:.88rem;color:var(--muted)}
.fnode{text-align:left;background:var(--panel);color:var(--text);border:1px solid var(--rule);border-radius:8px;padding:6px 10px;font:inherit;font-size:.9rem;cursor:pointer;max-width:100%;white-space:normal}
.fnode:hover,.fnode.active{border-color:var(--accent)}
.fnode.linked{border-color:var(--rule-strong);background:var(--panel-2)}
.fedges{margin:10px 0 0;font-size:.9rem;color:var(--muted)}
.fedges summary{cursor:pointer}
.fedges li.on{color:var(--text)}
.ranks,.forms{margin:10px 0 0;padding-left:1.4em}
.ranks li,.forms li{margin:4px 0}
.mgroup{margin:12px 0 0;color:var(--muted);font-size:.88rem}

@media (max-width:900px){
  .ex-layout{grid-template-columns:minmax(0,1fr);gap:16px}
  .ex-rail{position:static;max-height:none;overflow:visible;padding-bottom:0}
  .ex-rail ol{display:flex;overflow-x:auto;gap:4px;padding-bottom:6px;scrollbar-width:thin}
  .ex-rail li{flex:none}
  .ex-rail li.tier{display:none}
  .ex-rail button{border-left:0;border-bottom:2px solid transparent;border-radius:6px 6px 0 0;white-space:nowrap}
  .ex-rail button.active{border-bottom-color:var(--accent)}
  .ex-main{max-width:none}
}
@media (max-width:640px){
  .ex-head{grid-template-columns:minmax(0,1fr);grid-template-areas:"title" "actions" "meta";align-items:start}
  .roles{grid-template-columns:1fr}
  .chapter>.kicker+h2{font-size:22px}
  .chapter h2{font-size:17.5px}
  .ex-main{font-size:15.5px}
}
@media (prefers-reduced-motion:reduce){.progress div,.walk li{transition:none}}
"""


def scope_css(css: str, scope: str = ".ex") -> str:
    """Every rule of the stylesheet under `scope`, so the page's own names (`.card`, `.btn`, `h2`,
    `table`) never reach the site's bar, menus or command bar. The base rules (`:root`, `html`,
    `body`, `*`, `[hidden]`), keyframes and rules already written for the scope stay as they are.
    One level of `@media` is walked; the stylesheet has no deeper nesting."""
    keep = (":root", "html", "body", "*", "[hidden]", scope)
    out, i = [], 0
    while i < len(css):
        brace = css.find("{", i)
        if brace < 0:
            out.append(css[i:])
            break
        head = css[i:brace]
        lead = head[:len(head) - len(head.lstrip())]
        selector = head.strip()
        if selector.startswith("/*"):
            end = css.index("*/", i) + 2
            out.append(css[i:end])
            i = end
            continue
        depth, j = 1, brace + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        block = css[brace + 1:j - 1]
        if selector.startswith("@media"):
            out.append(f"{lead}{selector}{{{scope_css(block, scope)}}}")
        elif selector.startswith("@"):
            out.append(css[i:j])
        else:
            parts = [part.strip() for part in selector.split(",")]
            whole = re.compile(re.escape(scope) + r"(?![\w-])")
            parts = [part if part.startswith(keep[:-1]) or whole.match(part) else f"{scope} {part}" for part in parts]
            out.append(f"{lead}{','.join(parts)}{{{block}}}")
        i = j
    return "".join(out)

JS = r"""
(function(){
'use strict';
var chapters=[].slice.call(document.querySelectorAll('.chapter'));
var root=document.querySelector('.ex')||document.body;
var navButtons=[].slice.call(document.querySelectorAll('.ex-rail button'));
var bar=document.querySelector('.ex .progress div');
var label=document.getElementById('ex-progress-label');
var views=[].slice.call(document.querySelectorAll('.ex-view button'));
var current=0;
function toChapterTop(){
  var layout=document.querySelector('.ex-layout');if(!layout)return window.scrollTo(0,0);
  var lift=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--bar-h'))||parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--gn-bar-h'))||0;
  var top=layout.getBoundingClientRect().top+window.pageYOffset-lift-16;
  if(window.pageYOffset>top)window.scrollTo(0,Math.max(0,top));
}
function show(i,push){
  current=Math.max(0,Math.min(chapters.length-1,i));
  chapters.forEach(function(c,n){c.classList.toggle('active',n===current);});
  navButtons.forEach(function(b,n){b.classList.toggle('active',n===current);});
  bar.style.width=((current+1)/chapters.length*100)+'%';
  if(label)label.textContent='Chapter '+(current+1)+' of '+chapters.length;
  document.getElementById('prev').disabled=current===0;
  document.getElementById('next').disabled=current===chapters.length-1;
  [].forEach.call(document.querySelectorAll('[data-goto]'),function(b){b.classList.toggle('active',parseInt(b.getAttribute('data-goto'),10)===current+1);});
  if(push!==false){try{history.replaceState(null,'','#'+chapters[current].id);}catch(e){}}
  if(push!==false){if(root.classList.contains('all')){if(chapters[current].scrollIntoView)chapters[current].scrollIntoView();}else{toChapterTop();}}
}
function fromHash(){var m=/^#ch-(\d+)/.exec(location.hash);show(m?parseInt(m[1],10)-1:0,false);}
navButtons.forEach(function(b,n){b.addEventListener('click',function(){show(n);});});
document.getElementById('prev').addEventListener('click',function(){show(current-1);});
document.getElementById('next').addEventListener('click',function(){show(current+1);});
document.addEventListener('keydown',function(e){
  if(e.target&&/INPUT|SELECT|TEXTAREA|BUTTON/.test(e.target.tagName))return;
  if(e.key==='ArrowRight')show(current+1); if(e.key==='ArrowLeft')show(current-1);});
function setView(v){
  root.classList.toggle('all',v==='all');
  views.forEach(function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-view')===v));});
  if(v==='all'){var c=chapters[current];if(c&&c.scrollIntoView)c.scrollIntoView();}
}
views.forEach(function(b){b.addEventListener('click',function(){setView(b.getAttribute('data-view'));});});
window.addEventListener('hashchange',fromHash);
fromHash();

/* quizzes */
[].forEach.call(document.querySelectorAll('.quiz'),function(q){
  var why=q.querySelector('.quiz-why');
  [].forEach.call(q.querySelectorAll('.quiz-opt'),function(b){
    b.addEventListener('click',function(){
      var right=b.getAttribute('data-right')==='1';
      [].forEach.call(q.querySelectorAll('.quiz-opt'),function(x){x.classList.remove('wrong');});
      b.classList.add(right?'right':'wrong');
      if(right){[].forEach.call(q.querySelectorAll('.quiz-opt'),function(x){if(x.getAttribute('data-right')==='1')x.classList.add('right');});}
      why.hidden=false;
      why.textContent=(right?'Right. ':'Not quite. ')+why.getAttribute('data-text');
    });
  });
  why.setAttribute('data-text',why.textContent);
});

/* assumption chain */
[].forEach.call(document.querySelectorAll('[data-widget="assumption-chain"]'),function(w){
  var note=w.querySelector('[data-note]');var cards=w.querySelectorAll('.card.a');var outlook=w.querySelector('.card.outlook');
  w.addEventListener('click',function(e){
    var act=e.target.getAttribute&&e.target.getAttribute('data-act'); if(!act)return;
    if(act==='trip'){
      cards[1].classList.add('found');
      setTimeout(function(){cards[1].classList.add('broken');outlook.innerHTML='Outlook: Visayas supply margin for 21 September 2026 is <b>comfortable</b>? One assumption under it is now in doubt.';},600);
      note.textContent='The desk found the one assumption the notice touches. The other two are untouched. Now the analyst has to decide whether the outlook still holds.';
    } else {
      [].forEach.call(cards,function(c){c.classList.remove('found','broken');});
      outlook.innerHTML='Outlook: Visayas supply margin for 21 September 2026 is <b>comfortable</b>.';
      note.textContent='Nothing has happened yet.';
    }
  });
});

/* three grids */
[].forEach.call(document.querySelectorAll('[data-widget="three-grids"]'),function(w){
  var note=w.querySelector('[data-note]');var parts=w.querySelectorAll('[data-info]');
  function pick(el){[].forEach.call(parts,function(p){p.classList.remove('active');});el.classList.add('active');note.textContent=el.getAttribute('data-info');}
  [].forEach.call(parts,function(p){p.addEventListener('mouseenter',function(){pick(p);});p.addEventListener('click',function(){pick(p);});});
});

/* PEDC clock */
[].forEach.call(document.querySelectorAll('[data-widget="pedc-clock"]'),function(w){
  var r=w.querySelector('.clock'),t=w.querySelector('[data-time]'),s=w.querySelector('[data-state]'),ev=w.querySelectorAll('[data-events] li');
  function pad(n){return (n<10?'0':'')+n;}
  function update(){
    var m=parseInt(r.value,10);t.textContent=pad(Math.floor(m/60))+':'+pad(m%60);
    var state='Unit 2 on line. The assumption of 83.7 MW looks fine.',cls='ok';
    if(m>=814&&m<907){state='Unit 2 is off. The day-level assumption no longer matches what the grid sees.';cls='bad';}
    else if(m>=907&&m<1020){state='Unit 2 is back. Was the assumption wrong, or only for 93 minutes? The analyst decides.';cls='warn';}
    else if(m>=1020&&m<1200){state='Yellow alert. The reserve is low. The unit is back.';cls='warn';}
    else if(m>=1200){state='The alert ended at 20:00. Unit 2 on line.';cls='ok';}
    s.textContent=state;s.className='state '+cls;
    [].forEach.call(ev,function(li){var at=parseInt(li.getAttribute('data-at'),10);li.classList.toggle('past',m>=at);li.classList.toggle('now',m>=at&&m<at+15);});
  }
  r.addEventListener('input',update);update();
});

/* cutoff pair */
[].forEach.call(document.querySelectorAll('[data-widget="cutoff-pair"]'),function(w){
  var note=w.querySelector('[data-note]');var btns=w.querySelectorAll('[data-cut]');var p=w.querySelector('[data-known="t1"]');
  [].forEach.call(btns,function(b){b.addEventListener('click',function(){
    [].forEach.call(btns,function(x){x.classList.remove('active');});b.classList.add('active');
    var after=b.getAttribute('data-cut')==='t1';p.classList.toggle('known',after);
    note.textContent=after?'One second later, the notice is known. The desk reads it with the register. Gemini answered: challenges. The return notice stays outside: it was not known yet.':'Before the notice, the desk may read only the register. The answer should be: the assumption stands.';
  });});
});

/* question set */
[].forEach.call(document.querySelectorAll('[data-widget="question-set"]'),function(w){
  var note=w.querySelector('[data-note]');
  [].forEach.call(w.querySelectorAll('.questions li'),function(li){li.addEventListener('click',function(){note.textContent=li.getAttribute('data-plain');});});
  var btn=w.querySelector('[data-act="wordings"]'),box=w.querySelector('.wordings');
  btn.addEventListener('click',function(){box.hidden=!box.hidden;btn.textContent=box.hidden?'Show the four forms of Q2 on the trip run':'Hide the four forms';});
});

/* label rule */
[].forEach.call(document.querySelectorAll('[data-widget="label-rule"]'),function(w){
  var out=w.querySelector('[data-label]'),note=w.querySelector('[data-note]');
  function v(q){return w.querySelector('[data-q="'+q+'"]').value;}
  function run(){
    var label,why;
    if(v('stable')==='no'){label='not enough evidence';why='The four presentation forms disagreed, so the desk trusts none of the answers.';}
    else if(v('q7')==='no'){label='not enough evidence';why='The model said the passages do not suffice. Nothing else counts.';}
    else if(v('q2')==='other'){label='unrelated';why='The event has nothing to do with this assumption.';}
    else if(v('q2')==='commercial operation'&&v('q3')==='same'){label='supports';why='The unit starts commercial operation on the same day. The assumption holds.';}
    else if(v('q2')==='testing'){label='challenges';why='Testing is not commercial operation. The milestone does not match.';}
    else if(v('q2')==='forced outage'||v('q3')==='after'){label='challenges';why='A forced outage, or a later date, challenges an availability assumption.';}
    else if(v('q3')==='before'){label='mixed';why='An earlier observation, but the direction answer on the trip says challenges, so the rules give mixed.';}
    else {label='mixed';why='The time is not stated, and the direction answer names a direction, so the support is partial.';}
    out.textContent=label;out.className=label.replace(/ /g,'-').replace('not-enough-evidence','insufficient');
    note.textContent=why+' The judgment records the rule that fired.';
  }
  [].forEach.call(w.querySelectorAll('select'),function(s){s.addEventListener('change',run);});run();
});

/* practice decision */
[].forEach.call(document.querySelectorAll('[data-widget="practice-decision"]'),function(w){
  var form=w.querySelector('[data-form]'),hist=w.querySelector('[data-history]'),note=w.querySelector('[data-note]');
  var names={keep:'keep the assumption at 83.7 MW',change:'change the assumption',open:'open the assumption for review'};
  form.addEventListener('submit',function(e){
    e.preventDefault();
    var reason=w.querySelector('[data-reason]').value.trim();
    if(!reason){note.textContent='The desk refuses a decision without a reason. Write one sentence.';return;}
    var d=form.querySelector('input[name=d]:checked').value;
    var li=document.createElement('li');li.className='new';
    li.textContent='13:4'+(hist.children.length)+', you: '+names[d]+'. Reason: "'+reason+'". Judgment at that time: challenges.';
    [].forEach.call(hist.children,function(c){c.classList.remove('new');});hist.appendChild(li);
    note.textContent=(d==='keep'?'A kept assumption with a reason counts as success. ':'')+'Saved to the history of your own copy. The AI did not decide. You did.';
    w.querySelector('[data-reason]').value='';
  });
});


/* finding -> mechanism */
[].forEach.call(document.querySelectorAll('[data-widget="finding-mechanism"]'),function(w){
  var M=['Code composes the label from the modal top answers. The thresholds test the modal answer as 1.0 or 0.0, never a probability, so calibration does not enter the label.',
    'Each question comes in four presentation forms: another option order, bracketed numbers for the options of a choice question, and reversed passages. Above a flip rate of 0.25 the set is unstable, and the label becomes not enough evidence.',
    'Each yes/no question also comes in a negated form, and the desk turns the answer back. A polarity gap above 0.3 makes the set unstable.',
    'Question 7 asks whether the passages suffice to decide. A modal no makes the label not enough evidence, and so does an unknown identity. That label is an answer, not a failure.',
    'The compiled task holds only passages whose known-at time is at or before the cutoff. A passage with no known availability time stays out, and nobody fills one in.',
    'The compiled task holds only the permitted passages. Authority and routing stay in code. A sentence in the evidence that gives instructions is data, not an instruction.'];
  var out=w.querySelector('[data-mech]');
  w.addEventListener('click',function(e){var f=e.target.getAttribute&&e.target.getAttribute('data-f'); if(f==null)return; [].forEach.call(w.querySelectorAll('[data-f]'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=M[+f];});
});
/* layer stack */
[].forEach.call(document.querySelectorAll('[data-widget="layer-stack"]'),function(w){
  var L=['Owns: fixed source versions with fingerprints, exact passages, series references, and the time each one became known. Never grants: factual acceptance of a claim. A copy of a claim is not a second source.',
    'Owns: the access filter, the availability and cutoff filter, reviewed identity mappings, units and quantity kinds. Never grants: equality from a similar name. A fuzzy match cannot change a belief.',
    'Owns: the fixed selection and layout of one task: actor, case, belief version, cutoff, permitted passages and one fingerprint. Never grants: any authority to a model. Compiling selects. It does not judge.',
    'Owns: answers inside the compiled task only. The question set returns typed option answers. Never grants: a label composed from model confidence, or acceptance of anything.',
    'Owns: the composed label, the rule that fired, the stability record, and escalation when the label is not enough evidence or the judgment is unstable. Never grants: a change to a belief. It proposes.',
    'Owns: the analyst\'s decision with a required reason, written with the head change and the audit entry in one transaction. Never grants: execution of anything, or permission to run a forecast.',
    'Owns: the outlook history, the earlier and the new positions, the open issues, and the typed proposal for the forecasting process. Never grants: forecast skill or commercial value. Those need evaluation.'];
  var out=w.querySelector('[data-info]');
  w.addEventListener('click',function(e){var l=e.target.getAttribute&&e.target.getAttribute('data-l'); if(l==null)return; [].forEach.call(w.querySelectorAll('.layer'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=L[+l];});
});
/* record axes */
[].forEach.call(document.querySelectorAll('[data-widget="record-axes"]'),function(w){
  var out=w.querySelector('[data-read]');
  function v(k){return w.querySelector('[data-ax="'+k+'"]').value;}
  function run(){
    var kind=v('kind'),rev=v('review'),av=v('avail'),mode=v('mode'); var t=[];
    t.push('This record is '+(kind==='observation'?'an observation: something that happened':kind==='assumption'?'an assumption: a position the analyst holds':kind==='prediction'?'a prediction: a model output about the future':kind==='reported claim'?'a reported claim: what a source says':kind==='review decision'?'a review decision: the analyst\'s act':'a '+kind)+'.');
    t.push('Its review state is '+rev+'.'+(rev==='accepted'&&kind==='prediction'?' Accepting it does not make it an observation; it stays a prediction the desk relies on.':'' ));
    t.push(av==='verified by cutoff'?'It was known at the cutoff, so a strict judgment may read it.':av==='later than cutoff'?'It became known after the cutoff, so a strict judgment must not see it.':av==='unknown'?'Nobody can say when it became known, so it is excluded from strict context and shown only in a labelled exploratory section.':'Access is denied: it does not exist for this actor, and the count does not reveal it.');
    t.push('It was produced in mode '+mode+(mode==='stored run'?': the answers were produced once and saved; the view says so.':mode==='synthetic test data'?': made up for a test, labelled so, never shown as real.':mode==='retrospective replay'?': judged today against a historical cutoff; never shown as a decision made then.':'.'));
    out.textContent=t.join(' ');
  }
  [].forEach.call(w.querySelectorAll('select'),function(s){s.addEventListener('change',run);}); run();
});
/* cutoff slider, in seconds: a notice posted at 13:39:37 is admitted at 13:39:37, not at 13:39:00 */
[].forEach.call(document.querySelectorAll('[data-widget="cutoff-slider"]'),function(w){
  var r=w.querySelector('.clock'),t=w.querySelector('[data-time]'),c=w.querySelector('[data-count]'),note=w.querySelector('[data-note]'),ps=w.querySelectorAll('[data-list] .passage');
  function pad(n){return (n<10?'0':'')+n;}
  function update(){
    var sec=+r.value; t.textContent=pad(Math.floor(sec/3600))+':'+pad(Math.floor(sec/60)%60)+':'+pad(sec%60); var n=0,x=0,u=0;
    [].forEach.call(ps,function(p){var k=p.getAttribute('data-known'); if(k==='unknown'){p.className='passage later';u++;return;} var known=+k<=sec; p.className='passage'+(known?' known':''); if(known)n++; else x++;});
    c.textContent=n+' admitted · '+x+' later than the cutoff · '+u+' unknown';
    note.textContent=sec<49177?'Before 13:39:37 the desk can read only the register. The trip has happened, but the feed has not logged the notice yet.':sec<57356?'The trip notice is in. The return notice is not: at this cutoff nobody could read it, so the model does not either.':'All four notices are in. The real-time schedule stays out: it has no recorded availability time, and the desk never fills one in.';
  }
  r.addEventListener('input',update); update();
});
/* transaction race */
[].forEach.call(document.querySelectorAll('[data-widget="transaction-race"]'),function(w){
  var steps=w.querySelectorAll('.walk li'),next=w.querySelector('[data-act="next"]'),reset=w.querySelector('[data-act="reset"]'),race=w.querySelector('[data-race]'),note=w.querySelector('[data-note]'); var n=0;
  function draw(){
    [].forEach.call(steps,function(li,i){li.classList.toggle('on',i<n);li.classList.toggle('now',i===n-1);
      if(li.hasAttribute('data-ok')){li.innerHTML='<b>Outcome.</b> '+(i<n?(race.checked?li.getAttribute('data-race'):li.getAttribute('data-ok')):'…');}
    });
    if(n===4&&race.checked){steps[4].style.display='none';}else{steps[4].style.display='';}
    next.disabled=n>=steps.length||(n>=4&&race.checked);
    note.textContent=race.checked&&n>=4?'The server wrote nothing. The page reloads the heads and the analyst decides again on the current state.':'The information cutoff stays the notice\'s. Only the audit cutoff moves.';
  }
  next.addEventListener('click',function(){n=Math.min(steps.length,n+1);draw();}); reset.addEventListener('click',function(){n=0;draw();}); race.addEventListener('change',draw); draw();
});
/* rule table: the fourteen rows of compose() in src/judgment/bundle.py, in its order */
[].forEach.call(document.querySelectorAll('[data-widget="rule-table"]'),function(w){
  var out=w.querySelector('[data-label]'),fired=w.querySelector('[data-fired]'),rows=w.querySelectorAll('[data-rows] tr');
  function v(q){return w.querySelector('[data-q="'+q+'"]').value;}
  function run(){
    var r,label,avail=v('avail')==='yes';
    if(v('stable')==='no'){r=0;label='not enough evidence';}
    else if(v('q7')==='no'){r=1;label='not enough evidence';}
    else if(v('q1')==='cannot_tell'){r=2;label='not enough evidence';}
    else if(v('q1')==='other'){r=3;label='unrelated';}
    else if(v('q2')==='other'||v('q2')==='grid_alert'){r=4;label='unrelated';}
    else if(v('q5')==='yes'){r=5;label='the earlier source\'s label, or not enough evidence';}
    else if(avail&&(v('q2')==='commercial_operation'||v('q2')==='return_to_service')&&v('q3')==='same'&&v('q4')==='no'){r=6;label='supports';}
    else if(avail&&v('q2')==='testing'){r=7;label='challenges';}
    else if(avail&&(v('q2')==='planned_outage'||v('q2')==='forced_outage'||v('q2')==='derating'||v('q3')==='after')){r=8;label='challenges';}
    else if(v('q3')==='before'&&v('q6')==='yes'){ if(v('q8')!=='challenges'){r=9;label='supports';} else {r=10;label='mixed';} }
    else if(v('q4')==='yes'&&(v('q3')==='same'||v('q3')==='before')){r=11;label='mixed';}
    else if(v('q3')==='not_stated'){r=12;label=v('q8')!=='neither'?'mixed':'not enough evidence';}
    else {r=13;label='not enough evidence';}
    [].forEach.call(rows,function(tr,i){tr.classList.toggle('fired',i===r);});
    out.textContent=label; out.className=label.indexOf('supports')===0?'supports':label==='unrelated'?'unrelated':label==='mixed'?'mixed':label==='challenges'?'challenges':'insufficient';
    fired.textContent='row '+(r+1)+' fired';
  }
  [].forEach.call(w.querySelectorAll('select'),function(s){s.addEventListener('change',run);}); run();
});
/* receipt sim */
[].forEach.call(document.querySelectorAll('[data-widget="receipt-sim"]'),function(w){
  var sel=w.querySelectorAll('[data-w]');
  function run(){
    var ans=[].map.call(sel,function(s){return s.value;}); var counts={}; ans.forEach(function(a){counts[a]=(counts[a]||0)+1;});
    var modal=Object.keys(counts).sort(function(a,b){return counts[b]-counts[a];})[0]; var flips=ans.filter(function(a){return a!==modal;}).length/ans.length;
    w.querySelector('[data-modal]').textContent=modal; w.querySelector('[data-flip]').textContent=flips.toFixed(2);
    var v=w.querySelector('[data-verdict]'); v.textContent=flips>0.25?'unstable: label becomes "not enough evidence"':'stable'; v.style.color=flips>0.25?'var(--bad)':'var(--ok)';
  }
  [].forEach.call(sel,function(s){s.addEventListener('change',run);}); run();
});
/* claim checker */
[].forEach.call(document.querySelectorAll('[data-widget="claim-checker"]'),function(w){
  var A=['Not allowed. The three-hour classifier flagged only 7 of 71 alert days before the operator\'s own notice. The desk reads notices. It does not beat them.',
    'Allowed. It is a recorded run of 14 October 2026 with a receipt: four presentation forms, eight questions, rule 9, and 9,743 tokens in. The grade is demonstrated.',
    'Not allowed. A judgment score is never an event probability. The label says what the evidence does to one belief, and nothing about the grid.',
    'Not allowed. Both scored 22 of 28, and the test split favours the single question, 8 of 10 against 7 of 10. The paper calls it a tie.',
    'Not allowed. The ranking lists what was unusual at the time, as evidence and not proof. Supply ranked first at 0.777, and the card names no cause.',
    'Allowed. The desk judges a decision by what people knew, not by its outcome. The paper writes this into its invariants.'];
  var out=w.querySelector('[data-answer]');
  w.addEventListener('click',function(e){var c=e.target.getAttribute&&e.target.getAttribute('data-c'); if(c==null)return; [].forEach.call(w.querySelectorAll('[data-c]'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=A[+c];});
});
/* pipeline layers */
[].forEach.call(document.querySelectorAll('[data-widget="pipeline-layers"]'),function(w){
  var L=['BigQuery external tables read the company\'s files where they are: five-minute prices and schedules, HVDC schedules, regional summaries, operator messages. Nothing is copied into Git.',
    'SQL builds one row per five-minute interval and region (292,839 rows to 29 September 2026), the price view, 253 parsed advisories and the alert windows they announce.',
    'Reserve condition labels from March 2026; 17 model inputs per row; a three-hour embargo between inputs and labels so nothing from the future leaks into training.',
    'A boosted-tree model trained locally and TabFM inside BigQuery tie on reserve-onset AUC (Visayas 0.947 against 0.943; Mindanao 0.967 against 0.961); zero-shot TimesFM alone is not competitive. TabFM ran once, on one context sample, with uncalibrated probabilities: a dated result, not rerun.',
    'One row per interval and region with fixed words: price band, reserve condition, shortfall severity, trend, import dependence, alert now and ahead. Alerts are rebuilt as of each interval from the advisories issued by then.',
    'The grid data build turns the exported snapshot into the small JSON files the page reads, under one content stamp. The event view and the event-type vectors travel with it. The build refuses an output folder that Git tracks.'];
  var out=w.querySelector('[data-info]');
  w.addEventListener('click',function(e){var l=e.target.getAttribute&&e.target.getAttribute('data-l'); if(l==null)return; [].forEach.call(w.querySelectorAll('.layer'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=L[+l];});
});
/* vector sum */
[].forEach.call(document.querySelectorAll('[data-widget="vector-sum"]'),function(w){
  var g=w.querySelector('[data-plot]'),note=w.querySelector('[data-note]'); var h=[0,0],pts=[[160,100]],names=[]; var MAX=90;
  function draw(){
    var s='';
    for(var i=1;i<pts.length;i++){s+='<line x1="'+pts[i-1][0]+'" y1="'+pts[i-1][1]+'" x2="'+pts[i][0]+'" y2="'+pts[i][1]+'" stroke="#f0b429" stroke-width="2"/>';}
    pts.forEach(function(p,i){s+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="'+(i===pts.length-1?5:3)+'" fill="'+(i===pts.length-1?'#f0b429':'#8ab4f8')+'"/>';});
    g.innerHTML=s;
  }
  w.addEventListener('click',function(e){
    var v=e.target.getAttribute&&e.target.getAttribute('data-v'); var act=e.target.getAttribute&&e.target.getAttribute('data-act');
    if(act==='reset'){h=[0,0];pts=[[160,100]];names=[];draw();note.textContent='Cleared. Add events again.';return;}
    if(!v)return; var d=v.split(',').map(Number); h=[h[0]+d[0],h[1]+d[1]]; var n=Math.hypot(h[0],h[1]); if(n>MAX){h=[h[0]*MAX/n,h[1]*MAX/n];}
    pts.push([160+h[0],100-h[1]]); names.push(e.target.textContent); draw();
    note.textContent='State after '+names.length+' events: ('+h[0].toFixed(0)+', '+h[1].toFixed(0)+')'+(n>MAX?', clipped to the maximum length':'')+'. Without the clip the order would not matter. The clip after each step keeps long days bounded, and once it engages the order does matter.';
  });
  draw();
});
/* cache classes */
[].forEach.call(document.querySelectorAll('[data-widget="cache-classes"]'),function(w){
  var A=['The page: Cache-Control: no-cache. The browser keeps a copy but revalidates every time, so a new build is seen at once; the page carries the current stamp in a meta tag.',
    'A design file under the stamp: public, max-age=31536000, immutable. Cached for a year; a changed byte changes the stamp and the URL.',
    'A replay file under the stamp: immutable too, and Firebase Hosting serves it from the edge. The first screen never touches the server.',
    'The same file without a stamp: no-store. The unversioned name exists for harnesses and is never cached.',
    'A session or any private answer: no-store. Nothing personal is ever cached by a proxy.',
    'The warm-up: no-store, so every visit really reaches the server once after the first paint.'];
  var out=w.querySelector('[data-answer]');
  w.addEventListener('click',function(e){var u=e.target.getAttribute&&e.target.getAttribute('data-u'); if(u==null)return; [].forEach.call(w.querySelectorAll('[data-u]'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=A[+u];});
});

/* request walk and task life */
[].forEach.call(document.querySelectorAll('[data-widget="request-walk"],[data-widget="task-life"],[data-widget="cold-timeline"],[data-kind="walk"]'),function(w){
  var steps=w.querySelectorAll('.walk li'),next=w.querySelector('[data-act="next"]'),reset=w.querySelector('[data-act="reset"]'),total=w.querySelector('[data-total]'),asleep=w.querySelector('[data-asleep]');
  var n=0;
  function draw(){
    var sum=0;
    [].forEach.call(steps,function(li,i){
      li.classList.toggle('on',i<n);li.classList.toggle('now',i===n-1);
      var t=li.querySelector('.t');
      if(li.hasAttribute('data-t')){
        var val=(asleep&&asleep.checked)?li.getAttribute('data-ct'):li.getAttribute('data-t');
        if(!t){t=document.createElement('span');t.className='t';li.appendChild(t);}
        t.textContent=i<n?val:'';
        if(i<n&&val)sum+=parseFloat(val);
      }
    });
    if(total)total.textContent=sum.toFixed(1)+' s so far';
    next.disabled=n>=steps.length;
  }
  next.addEventListener('click',function(){n=Math.min(steps.length,n+1);draw();});
  reset.addEventListener('click',function(){n=0;draw();});
  if(asleep)asleep.addEventListener('change',draw);
  draw();
});

/* the systems map: a node, the status filter and the arrows in order (DOC-4) */
[].forEach.call(document.querySelectorAll('[data-widget="systems-map"]'),function(w){
  var detail=w.querySelector('[data-detail]'),note=w.querySelector('[data-arrow-note]'),home=note.textContent;
  var arrows=[].slice.call(w.querySelectorAll('.arrow')),step=0;
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  /* A record is a link on the single-file copy. On the site the target is empty, so the detail
     shows the record's name and its path in the repository instead of a dead link. */
  function ref(label,href,path){
    if(href)return '<a href="'+esc(href)+'">'+esc(label)+'</a>';
    return esc(label)+' <code class="ref-path">'+esc(path)+'</code>';
  }
  function nodeOf(target){var t=target;while(t&&t!==w){if(t.getAttribute&&t.getAttribute('data-node'))return t;t=t.parentNode;}return null;}
  function pick(el){
    [].forEach.call(w.querySelectorAll('.node'),function(b){b.classList.toggle('active',b.getAttribute('data-node')===el.getAttribute('data-node'));});
    detail.innerHTML='<p class="d-name">'+esc(el.getAttribute('data-name'))+' <i class="st st-'+esc(el.getAttribute('data-status'))+'">'+esc(el.getAttribute('data-status'))+'</i></p>'
      +'<p><b>What it is.</b> '+esc(el.getAttribute('data-what'))+'</p>'
      +'<p><b>Its role.</b> '+esc(el.getAttribute('data-role'))+'</p>'
      +'<p><b>Status.</b> '+esc(el.getAttribute('data-status-note'))+'</p>'
      +'<p><b>Its numbers.</b> '+esc(el.getAttribute('data-numbers'))+' <small>('+ref(el.getAttribute('data-numbers-source-label'),el.getAttribute('data-numbers-source-href'),el.getAttribute('data-numbers-source-ref'))+')</small></p>'
      +'<p><b>Its source record.</b> '+ref(el.getAttribute('data-source-label'),el.getAttribute('data-source-href'),el.getAttribute('data-source-ref'))+'</p>';
  }
  [].forEach.call(w.querySelectorAll('.node'),function(b){b.addEventListener('click',function(){pick(b);});});
  var filters=w.querySelectorAll('[data-filter]');
  [].forEach.call(filters,function(b){b.addEventListener('click',function(){
    var f=b.getAttribute('data-filter'),dimmed=0;
    [].forEach.call(filters,function(x){var on=x===b;x.classList.toggle('active',on);x.setAttribute('aria-pressed',on?'true':'false');});
    [].forEach.call(w.querySelectorAll('.node'),function(el){var hide=f!=='all'&&el.getAttribute('data-status')!==f;el.classList.toggle('dim',hide);if(hide)dimmed++;});
    note.textContent=f==='all'?home:dimmed+' nodes are not '+f+'. Nothing is hidden: the rest of the map stays in place.';
  });});
  function drawArrows(){
    [].forEach.call(arrows,function(a,i){a.classList.toggle('on',i<step-1);a.classList.toggle('now',i===step-1);});
    note.textContent=step===0?home:'Arrow '+step+' of '+arrows.length+'. '+arrows[step-1].getAttribute('title');
  }
  w.querySelector('[data-act="next-arrow"]').addEventListener('click',function(){step=step>=arrows.length?1:step+1;drawArrows();});
  w.querySelector('[data-act="reset-arrows"]').addEventListener('click',function(){step=0;drawArrows();});
  drawArrows();
});

/* the path: a line per chapter, a pointer into the chapter and a done mark in the reader's browser (DOC-4) */
[].forEach.call(document.querySelectorAll('[data-widget="path"]'),function(w){
  var note=w.querySelector('[data-path-note]'),KEY='nowcast-explainer-done',total=w.querySelectorAll('[data-done]').length;
  function read(){try{var v=JSON.parse(window.localStorage.getItem(KEY)||'[]');return Object.prototype.toString.call(v)==='[object Array]'?v:[];}catch(e){return [];}}
  function write(v){try{window.localStorage.setItem(KEY,JSON.stringify(v));}catch(e){}}
  var done=read();
  function draw(){
    var n=0;
    [].forEach.call(w.querySelectorAll('[data-done]'),function(b){var on=done.indexOf(b.getAttribute('data-done'))>=0;if(on)n++;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on?'true':'false');});
    note.textContent=n===0?'No chapter carries a done mark yet.':n+' of '+total+' chapters carry a done mark in this browser.';
  }
  [].forEach.call(w.querySelectorAll('[data-done]'),function(b){b.addEventListener('click',function(){
    var id=b.getAttribute('data-done'),i=done.indexOf(id);
    if(i>=0){done.splice(i,1);}else{done.push(id);}
    write(done);draw();
  });});
  [].forEach.call(w.querySelectorAll('[data-goto]'),function(b){b.addEventListener('click',function(){show(parseInt(b.getAttribute('data-goto'),10)-1);});});
  draw();
});

/* the two Gemini roles: the real PEDC example (DOC-4) */
[].forEach.call(document.querySelectorAll('[data-widget="ai-roles"]'),function(w){
  var b=w.querySelector('[data-act="example"]'),box=w.querySelector('[data-example]');
  b.addEventListener('click',function(){box.hidden=!box.hidden;b.textContent=box.hidden?'Show the real PEDC example':'Hide the real PEDC example';});
});

/* the belief, its source and its time span (DOC-5) */
[].forEach.call(document.querySelectorAll('[data-widget="belief-span"]'),function(w){
  var note=w.querySelector('[data-note]');
  var src=w.querySelector('[data-part="source"]'),span=w.querySelector('[data-part="span"]');
  var srcText='<b>The source.</b> A driver\'s report, this morning.',spanText='<b>The time span.</b> Today.';
  var rest='Nothing has changed yet. A belief holds while its source and its time span hold.';
  w.addEventListener('click',function(e){
    var act=e.target.getAttribute&&e.target.getAttribute('data-act'); if(!act)return;
    if(act==='source'){src.innerHTML='<b>The source.</b> A rumour from a passer-by.';src.classList.remove('known');note.textContent='The source is weaker now. The desk keeps the belief and asks for a better source before anyone acts on it.';}
    else if(act==='span'){span.innerHTML='<b>The time span.</b> The whole week.';span.classList.remove('known');note.textContent='The belief now claims the whole week, and nothing supports that yet. The desk opens the belief for a fresh review.';}
    else {src.innerHTML=srcText;span.innerHTML=spanText;src.classList.add('known');span.classList.add('known');note.textContent=rest;}
  });
});

/* the decision, its line and its cost (DOC-5) */
[].forEach.call(document.querySelectorAll('[data-widget="decision-line"]'),function(w){
  var r=w.querySelector('input[type=range]'),out=w.querySelector('[data-amount]'),v=w.querySelector('[data-verdict]');
  var LINE=1000000;
  function fmt(n){return String(n).replace(/\B(?=(\d{3})+(?!\d))/g,',');}
  function run(){
    var n=parseInt(r.value,10),over=n>=LINE;
    out.textContent=fmt(n)+' PHP';
    v.textContent=over?'At or above the line. The change matters, so the cost goes to the decision.':'Below the line. The desk leaves the position where it is.';
    v.className='state '+(over?'warn':'ok');
  }
  r.addEventListener('input',run); run();
});

/* the loop, one stage lit at a time (DOC-5) */
[].forEach.call(document.querySelectorAll('[data-widget="loop-stages"]'),function(w){
  var stages=w.querySelectorAll('.stage'),info=w.querySelector('[data-info]');
  var T=['Knowledge. The desk records the evidence with its source and the time it became known. The record is the desk\'s own work.',
    'Judgment. The model answers fixed questions and proposes a reading. It never accepts, and its answers stay on the record.',
    'Work. The analyst decides, keeps a reason and accepts or refuses the change. One write keeps the act, and that act is the receipt.',
    'Learning. The settled month scores the forecast. The first real pair is November to December 2026, and nothing reads the score yet.'];
  var n=0;
  function draw(){[].forEach.call(stages,function(s,i){s.classList.toggle('on',i<n);s.classList.toggle('now',i===n-1);});info.textContent=n===0?'Press Next to start.':T[n-1];}
  w.querySelector('[data-act="next"]').addEventListener('click',function(){n=n>=stages.length?1:n+1;draw();});
  w.querySelector('[data-act="reset"]').addEventListener('click',function(){n=0;draw();});
  draw();
});

/* the miss and its cause: belief, late signal, method (DOC-5) */
[].forEach.call(document.querySelectorAll('[data-widget="miss-cause"]'),function(w){
  var out=w.querySelector('[data-info]');
  var C=['The belief was wrong, so the belief changes and the position that rested on it comes back for review. The action or the belief is corrected: the first loop.',
    'The signal arrived after the cutoff, so the desk judged with what was known then, and the decision stands as it was made. What changes is when the desk looks.',
    'The method was wrong: the questions, the words or the line. The belief may still stand, and the rule table or the model goes back to the bench. The method or the goal changes: the second loop.'];
  w.addEventListener('click',function(e){var c=e.target.getAttribute&&e.target.getAttribute('data-c'); if(c==null)return; [].forEach.call(w.querySelectorAll('[data-c]'),function(b){b.classList.toggle('active',b===e.target);}); out.textContent=C[+c];});
});
/* the companion (third part): pick, switch, figure and the view validator */
function closest(el,sel,root){while(el&&el!==root){if(el.matches&&el.matches(sel))return el;el=el.parentNode;}return null;}
[].forEach.call(document.querySelectorAll('[data-kind="pick"]'),function(w){
  var out=w.querySelector('[data-out]');
  w.addEventListener('click',function(e){var b=closest(e.target,'[data-say]',w); if(!b)return;
    [].forEach.call(w.querySelectorAll('[data-say]'),function(x){x.classList.toggle('active',x===b);}); out.textContent=b.getAttribute('data-say');});
});
[].forEach.call(document.querySelectorAll('[data-kind="switch"]'),function(w){
  var state={};
  [].forEach.call(w.querySelectorAll('[data-set].active'),function(b){var p=b.getAttribute('data-set').split(':');state[p[0]]=p[1];});
  function draw(){
    [].forEach.call(w.querySelectorAll('[data-set]'),function(b){var p=b.getAttribute('data-set').split(':'),on=state[p[0]]===p[1];b.classList.toggle('active',on);b.setAttribute('aria-pressed',on?'true':'false');});
    [].forEach.call(w.querySelectorAll('[data-when]'),function(el){el.hidden=!el.getAttribute('data-when').split(' ').every(function(c){var p=c.split(':');return state[p[0]]===p[1];});});
  }
  w.addEventListener('click',function(e){var b=closest(e.target,'[data-set]',w); if(!b)return; var p=b.getAttribute('data-set').split(':'); state[p[0]]=p[1]; draw();});
  draw();
});
[].forEach.call(document.querySelectorAll('[data-kind="figure"]'),function(w){
  var d=w.querySelector('[data-detail]'),edges=[].slice.call(w.querySelectorAll('.fedges li'));
  function line(text){var p=document.createElement('p');p.textContent=text;d.appendChild(p);}
  w.addEventListener('click',function(e){var b=closest(e.target,'.fnode',w); if(!b)return;
    var id=b.getAttribute('data-id'),ins=[],outs=[];
    [].forEach.call(w.querySelectorAll('.fnode'),function(x){x.classList.remove('active');x.classList.remove('linked');});
    b.classList.add('active');
    edges.forEach(function(li){var a=li.getAttribute('data-a'),z=li.getAttribute('data-b');
      if(a===id||z===id){li.classList.add('on');var other=w.querySelector('.fnode[data-id="'+(a===id?z:a)+'"]'); if(other)other.classList.add('linked'); (a===id?outs:ins).push(li.textContent);} else li.classList.remove('on');});
    d.textContent=''; var h=document.createElement('p'),s=document.createElement('b'); s.textContent=b.textContent; h.appendChild(s);
    var g=closest(b,'.fgroup',w); if(g)h.appendChild(document.createTextNode(' · in '+g.querySelector('h4').textContent)); d.appendChild(h);
    line('Arrows in: '+(ins.length?ins.join(' · '):'none in this figure'));
    line('Arrows out: '+(outs.length?outs.join(' · '):'none in this figure'));
  });
});
[].forEach.call(document.querySelectorAll('[data-widget="view-validator"]'),function(w){
  var verdict=w.querySelector('[data-verdict]'),reasons=w.querySelector('[data-reasons]'),text=w.querySelector('[data-text]');
  var NAMES={cutoff:'the cutoff and the mode',families:'one block per family',unconfirmed:'the unconfirmed matches',withheld:'the withheld counts',ranking:'the ranking under its fixed heading'};
  function run(){
    var why=[];
    Object.keys(NAMES).forEach(function(k){if(!w.querySelector('[data-part="'+k+'"]').checked)why.push('Refused: the plan leaves out '+NAMES[k]+', a mandatory part of question kind Q1.');});
    if(w.querySelector('[data-part="chart"]').checked)why.push('Refused: a free chart is not in the catalogue. The model may only choose catalogue parts.');
    if(text.value==='numeral')why.push('Refused: the text holds the numeral 0.78, which quotes no record field by its id. The validator records the refusal.');
    verdict.textContent=why.length?'refused':'accepted'; verdict.className=why.length?'challenges':'supports';
    reasons.textContent=why.length?why.join(' '):(text.value==='quote'?'Every mandatory part is present, every part is in the catalogue, and the text quotes its one number by its field.':'Every mandatory part is present, every part is in the catalogue, and the text holds no numeral.');
  }
  [].forEach.call(w.querySelectorAll('input,select'),function(c){c.addEventListener('change',run);}); run();
});
})();
"""


def build_parts(site: bool = False) -> dict:
    """The page's body, its stylesheet and its script, built once from the chapters and the glossary.
    `site` builds the body of the page the site serves: there, each repository target is a reference
    that shows the record's path, and one note says where the records live."""
    terms = glossary_terms(GLOSSARY)
    files = sorted(p for p in CHAPTERS.glob("[0-9][0-9]-*.md"))
    if not files:
        raise SystemExit("no chapters found")
    names = [path.name for path in files]
    if sorted(names) != sorted(CHAPTER_ADD):
        raise SystemExit("CHAPTER_ADD must name every chapter file and no other file")
    if names != [name for _title, _note, part in PARTS for name in part]:
        raise SystemExit("PARTS must list every chapter file once, in reading order")
    part_of = {name: tier for tier, _note, part in PARTS for name in part}
    widgets = {**{name: widget_refs(markup, site) for name, markup in WIDGETS.items()},
               **generated_widgets(files, site)}
    sections, nav = [], []
    for n, path in enumerate(files, start=1):
        body, title, widget_count, quizzes = markdown(path.read_text(encoding="utf-8"), widgets, n, site)
        if not title:
            raise SystemExit(f"{path.name}: first line must be a level-one heading")
        if widget_count == 0 or quizzes == 0:
            raise SystemExit(f"{path.name}: each chapter needs one widget and one quiz (has {widget_count}, {quizzes})")
        body = mark_terms(chapter_strip(files, n) + "\n" + body, terms)
        sections.append(f'<section class="chapter" id="ch-{n}" data-source="{path.name}">\n'
                        f'<p class="kicker">Chapter {n} of {len(files)}</p>\n<h2>{inline(title, site)}</h2>\n{body}\n</section>')
        tier = part_of[path.name]
        if n == 1 or part_of[files[n - 2].name] != tier:
            nav.append(f'<li class="tier">{inline(tier, site)}</li>')
        nav.append(f'<li><button type="button"><span class="n">{n}</span><span>{inline(title, site)}</span></button></li>')
    ref_note = ('<p class="ref-note" data-ref-note>The site serves no Markdown. Each record on this page '
                "shows its path in the repository, where the record lives.</p>" if site else "")
    # ATG-8: the site's shared section navigation, on the served page only; the copy that opens from
    # disk has no site to navigate, so it keeps its bare header. ROUTES-1 adds Models, Work and Map
    # after Paper; the ask panel has no entry of its own.
    # The served page's top bar carries that navigation only; the page's own title and its
    # chapter toggle sit in the page header below it.
    sites = ('<div class="bar">' + BRAND + '<nav class="sites" aria-label="Sections"><a href="/">Grid</a><a href="/data">Data</a>'
             '<a href="/plants">Plants</a><a href="/explain" aria-current="page">Explain</a>'
             '<a href="/outlooks">Outlooks</a><a href="/paper">Paper</a>'
             '<a href="/models">Models</a><a href="/work">Work</a><a href="/map">Map</a>'
             '<a href="/alerts">Alerts</a></nav></div>\n' if site else "")
    # ROUTES-1: the desk assistant's mount point, on the served page only, after the title; the
    # copy that opens from disk has no site services and keeps none of this.
    ask = ('<section id="ask" data-context="explain" aria-label="Ask Ingrid"></section>\n'
           if site else "")
    # Platform polish (PP-B4): one page head (the title, one line on what the page is, the view
    # switch, then where the chapters live), and the chapter rail with the reader's progress at
    # its head. On the site the wrapper is also the shared page frame (`gn-page`).
    frame = "ex gn-page ex-page" if site else "ex"
    body = f"""{sites}{ask}<div class="{frame}">
<header class="ex-head">
<div class="ex-title"><p class="ex-eyebrow">How it works</p><h1>{TITLE}</h1>
<p class="ex-sub">{len(files)} short chapters, each with one widget to try and one question to check yourself.</p></div>
<div class="ex-actions"><div class="ex-view" role="group" aria-label="Show"><button type="button" data-view="one" aria-pressed="true">One chapter</button><button type="button" data-view="all" aria-pressed="false">All chapters</button></div></div>
<div class="ex-meta"><p>Source: the chapters under docs/explainer in the repository.</p>
{ref_note}</div>
</header>
<div class="ex-layout">
<nav class="ex-rail" aria-label="Chapters"><div class="ex-progress"><span class="ex-progress-label" id="ex-progress-label">Chapter 1 of {len(files)}</span><div class="progress"><div></div></div></div><ol>
{chr(10).join(nav)}
</ol></nav>
<main class="ex-main">
{chr(10).join(sections)}
<div class="pager"><button type="button" class="btn ghost" id="prev">Previous chapter</button><button type="button" class="btn primary" id="next">Next chapter</button></div>
</main>
</div>
</div>"""
    return {"body": body, "css": scope_css(CSS.strip("\n")) + "\n", "js": JS.strip("\n") + "\n"}


#: The served page's brand link, the same one every grid page's top bar opens with.
BRAND = ('<a class="brand" href="/" aria-label="InGRID home"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 15 8 6l4 6 2-3 3 6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/></svg><span>InGRID</span></a>')


def site_page() -> str:
    """The page the site serves: no inline code (the content security policy admits none), the
    stylesheet and the script under the build-stamped prefix, like the grid pages, and the body
    built for the site, where a repository target is a reference and never a dead link."""
    parts = build_parts(site=True)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta id="nowcast-build" name="nowcast-build" content="{STAMP_TOKEN}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>How it works · About · InGRID</title>
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#0b1018" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f4f6fa" media="(prefers-color-scheme: light)">
<link rel="stylesheet" href="/grid/{STAMP_TOKEN}/explain.css">
<link rel="stylesheet" href="/grid/{STAMP_TOKEN}/ask.css">
<link rel="stylesheet" href="/grid/{STAMP_TOKEN}/ui.css">
<link rel="stylesheet" href="/grid/{STAMP_TOKEN}/shell.css">
<script src="/grid/{STAMP_TOKEN}/shell.js"></script>
<script src="/grid/{STAMP_TOKEN}/explain.js" defer></script>
<script src="/grid/{STAMP_TOKEN}/ask.js" defer></script>
</head>
<body>
{parts["body"]}
</body>
</html>
"""


def build() -> str:
    """The single-file copy that opens from disk: the same body with the style and script inline."""
    parts = build_parts()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>{TITLE}</title>
<style>{parts["css"]}</style>
</head>
<body>
{parts["body"]}
<script>{parts["js"]}</script>
</body>
</html>
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Exit 1 if the committed page differs from a fresh build")
    parser.add_argument("--out", default=str(OUTPUT))
    args = parser.parse_args(argv)
    parts = build_parts()
    outputs = {Path(args.out): build(), SITE / "explain.html": site_page(),
               SITE / "explain.css": parts["css"], SITE / "explain.js": parts["js"]}
    if args.check:
        stale = [str(path) for path, text in outputs.items()
                 if (path.read_text(encoding="utf-8") if path.exists() else "") != text]
        if stale:
            print("out of date, run %s to rebuild: %s" % (Path(__file__).name, ", ".join(stale)), file=sys.stderr)
            return 1
        print("the page, its three site files and the chapters agree")
        return 0
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path} ({len(text.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
