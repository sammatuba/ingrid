"""Render the showcase records (strategy, deck storyline, storyboard) into one self-contained HTML
file for offline reading: docs/work/showcase-2026-10-18/showcase-pack.html. Repository links become
plain paths, because the file is read away from the repository. Run: python3 scripts/docs/build_showcase.py"""
from __future__ import annotations
import html, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_explainer import inline as _inline  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "docs/work/showcase-2026-10-18"
PARTS = [("strategy.md", "Strategy: the use cases and the decisions"),
         ("storyboard.md", "Video storyboard: shots, roles, narration"),
         ("deck-storyline.md", "Deck storyline: page by page")]


def inline(text: str, base: Path) -> str:
    def plain(m):
        label, href = m.group(1), m.group(2)
        if href.startswith(("http://", "https://")):
            return m.group(0)
        if href.startswith("#"):
            return m.group(0)
        target = (base / href.split("#")[0]).resolve()
        try:
            rel = target.relative_to(ROOT)
        except ValueError:
            rel = Path(href)
        return f"{label} (`{rel.as_posix()}`)"
    return _inline(re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", plain, text))


def render(text: str, base: Path) -> str:
    lines, out, i = text.splitlines(), [], 0
    para: list[str] = []

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para), base)}</p>")
            para.clear()

    def list_block(start: int) -> int:
        """Render a (possibly nested) bullet or numbered list starting at line `start`."""
        items, j = [], start
        while j < len(lines):
            m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[j])
            if m:
                items.append((len(m.group(1)), m.group(2), [m.group(3)]))
                j += 1
            elif lines[j].strip() and re.match(r"^\s{2,}\S", lines[j]) and items:
                items[-1][2].append(lines[j].strip())
                j += 1
            else:
                break
        def emit(level: int, k: int) -> tuple[str, int]:
            ordered = items[k][1][0].isdigit()
            tag = "ol" if ordered else "ul"
            h = [f"<{tag}>"]
            while k < len(items) and items[k][0] == level:
                h.append(f"<li>{inline(' '.join(items[k][2]), base)}")
                k += 1
                if k < len(items) and items[k][0] > level:
                    sub, k = emit(items[k][0], k)
                    h.append(sub)
                h.append("</li>")
            h.append(f"</{tag}>")
            return "\n".join(h), k
        k = 0
        while k < len(items):
            block, k = emit(items[k][0], k)
            out.append(block)
        return j

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush()
            level = len(m.group(1))
            text_ = m.group(2)
            anchor = re.sub(r"[^a-z0-9]+", "-", text_.lower()).strip("-")
            out.append(f'<h{level} id="{anchor}">{inline(text_, base)}</h{level}>')
            i += 1
            continue
        if line.startswith("|"):
            flush()
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            rows = lines[i:j]
            if len(rows) >= 2 and re.match(r"^\|\s*-", rows[1]):
                out.append(_table(rows, base))
            else:
                para.extend(rows)
            i = j
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            flush()
            i = list_block(i)
            continue
        if not line.strip():
            flush()
            i += 1
            continue
        para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


def _table(rows: list[str], base: Path) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], cells[2:]
    out = ["<table>", "<thead><tr>" + "".join(f"<th>{inline(c, base)}</th>" for c in head) + "</tr></thead>", "<tbody>"]
    for row in body:
        out.append("<tr>" + "".join(f"<td>{inline(c, base)}</td>" for c in row) + "</tr>")
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


CSS = """
:root{--bg:#fbfaf7;--text:#1d1d1b;--muted:#5a5a55;--rule:#d9d6cf;--accent:#1f5f8b;--code:#f0eee8}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{border-bottom:1px solid var(--rule);padding:20px 24px;background:#fff}
header h1{margin:0 0 4px;font-size:22px}header p{margin:0;color:var(--muted)}
nav{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--rule);padding:8px 24px;display:flex;gap:18px;flex-wrap:wrap;z-index:1}
nav a{color:var(--accent);text-decoration:none;font-weight:600}
main{max-width:1100px;margin:0 auto;padding:16px 24px 64px}
section.part{border-top:3px solid var(--accent);margin-top:36px;padding-top:12px}
section.part>h1{font-size:24px;margin:0 0 12px}
h2{font-size:19px;margin:28px 0 8px;border-bottom:1px solid var(--rule);padding-bottom:4px}
h3{font-size:16px;margin:22px 0 6px}h4{font-size:15px;margin:16px 0 4px}
p{margin:8px 0}a{color:var(--accent)}
code{background:var(--code);padding:1px 4px;border-radius:4px;font:13px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
pre{background:var(--code);padding:12px;border-radius:8px;overflow:auto;font-size:13px}pre code{background:none;padding:0}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:14px}
th,td{border:1px solid var(--rule);padding:6px 8px;vertical-align:top;text-align:left}th{background:#f3f1ec}
ul,ol{padding-left:22px}li{margin:3px 0}
.meta{color:var(--muted);font-size:13px}
@media print{nav{display:none}section.part{break-before:page}body{font-size:12px}}
"""


def main() -> int:
    parts = []
    for name, title in PARTS:
        text = (DIR / name).read_text(encoding="utf-8")
        text = re.sub(r"^# .*\n", "", text, count=1)
        slug = name.replace(".md", "")
        parts.append(f'<section class="part" id="{slug}"><h1>{html.escape(title)}</h1><p class="meta">Source: <code>docs/work/showcase-2026-10-18/{name}</code></p>\n{render(text, DIR)}\n</section>')
    nav = "".join(f'<a href="#{n.replace(".md", "")}">{html.escape(t.split(":")[0])}</a>' for n, t in PARTS)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>InGRID showcase pack: use cases, storyboard, deck</title><style>{CSS}</style></head>
<body><header><h1>InGRID showcase pack</h1><p>AI Builder Cup 2026 · the use cases, the video storyboard and the deck storyline · built from the records on main, 18 October 2026. Self-contained: no network needed. The judges' account is in the submission form only.</p></header>
<nav>{nav}</nav><main>{''.join(parts)}</main></body></html>"""
    out = DIR / "showcase-pack.html"
    out.write_text(page, encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: {out.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
