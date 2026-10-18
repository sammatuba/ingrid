"""The working paper page (/paper) is built from the paper's Markdown and keeps the site's rules."""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_paper", ROOT / "scripts/docs/build_paper.py")
build_paper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_paper)
SITE = ROOT / "src/grid"
SOURCE = ROOT / "docs/product/paper-accountable-ai-decisions-2026-10-17.md"


class PaperPage(unittest.TestCase):
    def test_committed_page_matches_a_fresh_build(self):
        self.assertEqual((SITE / "paper.html").read_text(encoding="utf-8"), build_paper.site_page(),
                         "src/grid/paper.html is out of date; run scripts/docs/build_paper.py")
        self.assertEqual((SITE / "paper.css").read_text(encoding="utf-8"), build_paper.CSS)

    def test_page_keeps_the_content_security_policy(self):
        page = (SITE / "paper.html").read_text(encoding="utf-8")
        # ROUTES-1: the page now loads one same-origin script, the desk assistant's ask.js,
        # under the policy's script-src 'self'. No inline script or style is admitted.
        self.assertNotRegex(page, r'<script(?![^>]*\bsrc=)[^>]*>')
        self.assertIn('<script src="/grid/__NOWCAST_STAMP__/ask.js" defer></script>', page)
        self.assertNotIn("<style", page)
        self.assertNotRegex(page, r"\son\w+=")
        self.assertIn('href="/grid/__NOWCAST_STAMP__/paper.css"', page)
        sources = re.findall(r'(?:src|href)="([^"]+)"', page)
        local = [s for s in sources if not s.startswith("https://")]
        self.assertTrue(all(s.startswith(("/", "#")) for s in local), local)
        self.assertNotIn("https://", " ".join(re.findall(r'<link[^>]+>', page)))

    def test_the_bar_carries_the_sections_navigation_with_paper_current(self):
        """NAV-1 and ROUTES-1: the paper's bar is the site's shared section navigation, built
        without inline code: the ten routes in order, and the paper's own entry marked current."""
        page = (SITE / "paper.html").read_text(encoding="utf-8")
        nav = re.search(r'<nav class="sites" aria-label="Sections">(.*?)</nav>', page, re.S)
        self.assertIsNotNone(nav, "the paper page carries the section navigation")
        links = re.findall(r'<a href="([^"]+)"([^>]*)>([^<]+)</a>', nav.group(1))
        self.assertEqual([("/", "Grid"), ("/data", "Data"), ("/plants", "Plants"),
                          ("/explain", "Explain"), ("/outlooks", "Outlooks"),
                          ("/paper", "Paper"), ("/models", "Models"), ("/work", "Work"),
                          ("/map", "Map"), ("/alerts", "Alerts")],
                         [(href, label) for href, attrs, label in links])
        self.assertEqual(["/paper"], [href for href, attrs, label in links
                                      if 'aria-current="page"' in attrs])

    def test_math_and_diagram_are_converted(self):
        page = (SITE / "paper.html").read_text(encoding="utf-8")
        self.assertNotIn("$", page)
        self.assertNotIn("PAPERSLOT", page)
        self.assertNotIn("mermaid", page)
        self.assertNotIn("\\", page)
        # six figures: the chain (5 boxes), the prototype (5), the four layers (4), the seven kinds (2),
        # the scoring loop (3) and the generative view (4)
        self.assertEqual(page.count('<section class="layer">'), 24)
        # PP-B4: each figure's list of links folds under its own disclosure.
        self.assertEqual(page.count('<summary class="edges-title">'), 6)
        self.assertIn("update beliefs · evaluate methods and models", page)
        self.assertIn("evidence, not proof", page)

    def test_the_page_sits_in_the_reading_frame(self):
        """PP-B4: the shared frame and component layer, a contents rail with one entry per
        section, the reading-progress hairline, section anchors, and each table and diagram in a
        figure with its caption."""
        page = (SITE / "paper.html").read_text(encoding="utf-8")
        head = page.split("</head>")[0]
        self.assertLess(head.index("/ui.css"), head.index("/shell.css"), "ui.css links just before shell.css")
        self.assertIn('<script src="/grid/__NOWCAST_STAMP__/reading.js" defer></script>', page)
        self.assertIn('<main class="gn-page pp-page">', page)
        sections = re.findall(r'<h2 id="([^"]+)">', page)
        rail = re.search(r'<nav class="pp-toc" aria-label="Contents" data-toc>(.*?)</nav>', page, re.S).group(1)
        self.assertEqual(sections, re.findall(r'<a href="#([^"]+)"', rail), "one rail entry per section, in order")
        self.assertGreaterEqual(len(sections), 20)
        self.assertIn('<div class="pp-progress" data-read-progress hidden><span></span></div>', page)
        self.assertIn('<article class="pp-article" data-read-target>', page)
        self.assertEqual(len(re.findall(r'<h[23] id="[^"]+">', page)),
                         page.count('<a class="pp-anchor"'), "every section heading carries its anchor")
        self.assertEqual(page.count("<table>"), page.count('<div class="pp-table-wrap"><table>'))
        captions = re.findall(r'<figcaption><span class="pp-cap-n">((?:Table|Figure) \d+)\.</span>', page)
        self.assertEqual(13, len([c for c in captions if c.startswith("Table")]))
        self.assertEqual(6, len([c for c in captions if c.startswith("Figure")]))
        self.assertNotIn("<p><em>Table ", page)
        self.assertNotIn("<p><em>Figure ", page)

    def test_reference_list_keeps_one_item_per_entry(self):
        """A continuation line that begins with a year ("  2026. https://...") must not split an entry."""
        source = SOURCE.read_text(encoding="utf-8")
        entries = source.split("## References")[1].split("## Appendix A")[0]
        expected = len(re.findall(r"^- ", entries, flags=re.M))
        page = (SITE / "paper.html").read_text(encoding="utf-8")
        rendered = page.split("References</h2>")[1].split("<h2")[0]
        items = re.findall(r"<li>(.*?)</li>", rendered, flags=re.S)
        self.assertEqual(len(items), expected)
        self.assertGreaterEqual(expected, 30)
        for item in items:
            self.assertRegex(item, r"\((?:19|20)\d\d[ab]?\)", item[:80])
            self.assertNotRegex(item, r"^\s*(?:19|20)\d\d\.", item[:80])

    def test_list_parser_keeps_a_year_continuation_inside_an_item(self):
        text = ("# Title\n\n"
                "- Doe, J. (2026). A paper. *Journal*, 1 January\n"
                "  2026. https://example.org/a\n"
                "- Roe, R. (2025). Another paper.\n")
        article, _, _, _ = build_paper.explainer.markdown(text, {}, 0, site=True)
        items = re.findall(r"<li>(.*?)</li>", article, flags=re.S)
        self.assertEqual(len(items), 2)
        self.assertIn("1 January 2026.", items[0])
        self.assertIn("example.org/a", items[0])
        ordered, _, _, _ = build_paper.explainer.markdown("# T\n\n1. one\n2. two\n", {}, 0, site=True)
        self.assertEqual(ordered.count("<li>"), 2)
        self.assertIn("<ol>", ordered)

    def test_tex_subset(self):
        self.assertEqual(build_paper.tex(r"t^{a}_s"), "<i>t</i><sup><i>a</i></sup><sub><i>s</i></sub>")
        self.assertEqual(build_paper.tex(r"a \le b"), "<i>a</i> ≤ <i>b</i>")
        self.assertEqual(build_paper.tex(r"x < y"), "<i>x</i> &lt; <i>y</i>")
        with self.assertRaises(SystemExit):
            build_paper.tex(r"\frac{a}{b}")


if __name__ == "__main__":
    unittest.main()
