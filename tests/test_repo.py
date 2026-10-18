"""Behavioral tests for offline routing, handoffs and link validation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("repo", Path(__file__).resolve().parents[1] / "scripts/repo.py")
repo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repo)


class RepositoryTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for value in ("AGENTS.md", "docs/status.md", "skill.md", "intent.md", "evidence.md", "review.md", "case.md"):
            self.write(value, "# Heading\n")
        self.write_json("docs/routes.json", {"version": 1, "bootstrap": ["AGENTS.md", "docs/status.md"],
            "routes": {p: ["skill.md"] for p in repo.PHASES}, "aliases": {"audit": "review"}})
        self.current = {"version": 1, "work_id": "default-case", "phase": "intent", "status": "awaiting_input",
            "references": ["case.md"], "blockers": ["Need the episode"], "next_action": "Select an episode"}
        self.write_json("docs/work/current.json", self.current)
        self.packet = {"version": 1, "id": "explicit-task", "phase": "review", "status": "in_progress",
            "base_commit": "abcdef1", "artifacts": {"intent": "intent.md", "implement": "evidence.md", "review": "review.md"},
            "blockers": [], "next_action": "Review the changes"}
        self.write_json("docs/work/explicit-task/work.json", self.packet)

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def write_json(self, path, data):
        return self.write(path, json.dumps(data))

    def test_explicit_work_overrides_default_and_loads_only_needed_phases(self):
        result = repo.route(self.root, "implement", "docs/work/explicit-task")
        self.assertIn("intent.md", result["files"])
        self.assertIn("evidence.md", result["files"])
        self.assertNotIn("review.md", result["files"])
        self.assertNotIn("case.md", result["files"])

    def test_default_handoff_discloses_blockers_without_preventing_reading(self):
        self.assertIn("case.md", repo.route(self.root, "intent")["files"])

    def test_review_alias_loads_review_evidence(self):
        result = repo.route(self.root, "audit", "docs/work/explicit-task")
        self.assertEqual("review", result["route"])
        self.assertIn("review.md", result["files"])

    def test_unknown_route_fails(self):
        with self.assertRaises(ValueError):
            repo.route(self.root, "deploy")

    def test_blocked_packet_cannot_be_marked_ready(self):
        self.packet.update(status="ready", blockers=["Unresolved scope"])
        with self.assertRaises(ValueError):
            repo.validate_handoff(self.root, self.packet, packet=True)

    def test_missing_artifact_fails(self):
        self.packet["artifacts"]["intent"] = "missing.md"
        with self.assertRaises(ValueError):
            repo.validate_handoff(self.root, self.packet, packet=True)

    def test_implement_requires_intent(self):
        del self.packet["artifacts"]["intent"]
        with self.assertRaises(ValueError):
            repo.validate_handoff(self.root, self.packet, packet=True)

    def test_outside_paths_are_rejected(self):
        for path in ("../outside.md", "/absolute.md", "C:/outside.md", "docs\\status.md"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                repo.local_path(self.root, path)

    def test_broken_links_and_anchors_are_reported(self):
        p = self.write("readme.md", "[bad](gone.md) [bad heading](intent.md#absent)")
        errors, count = repo.markdown_errors(self.root, p)
        self.assertEqual(2, len(errors))
        self.assertEqual(2, count)

    def test_examples_and_external_links_are_not_local_dependencies(self):
        p = self.write("readme.md", "[web](https://example.test/a)\n```md\n[example](missing.md)\n```\n")
        self.assertEqual(([], 0), repo.markdown_errors(self.root, p))

    def test_encoded_spaces_and_duplicate_heading_anchors(self):
        self.write("two words.md", "# Same\n# Same\n")
        p = self.write("readme.md", "[ok](two%20words.md#same-1)")
        self.assertEqual(([], 1), repo.markdown_errors(self.root, p))

    def test_reference_link_and_parent_escape(self):
        p = self.write("readme.md", "[ok]: intent.md#heading\n[bad]: ../outside.md\n")
        errors, count = repo.markdown_errors(self.root, p)
        self.assertEqual(1, len(errors))
        self.assertEqual(2, count)

    def test_generated_directories_are_not_discovered(self):
        self.write(".venv/ignored.md", "[bad](missing.md)")
        self.write(".agents/skills/example/SKILL.md", "# Visible")
        paths = {p.relative_to(self.root).as_posix() for p in repo.repository_files(self.root)}
        self.assertNotIn(".venv/ignored.md", paths)
        self.assertIn(".agents/skills/example/SKILL.md", paths)

    def test_additional_skills_allowed_but_meos_skills_required(self):
        self.write_json("docs/routes.json", {"version": 1, "bootstrap": ["AGENTS.md"],
            "bootstrap_word_budget": 1200, "routes": {p: ["skill.md"] for p in repo.PHASES}})
        for name in [*[f"meos-{p}" for p in repo.PHASES], "meos-wrapup", "local-extra"]:
            self.write(f".agents/skills/{name}/SKILL.md",
                       f"---\nname: {name}\ndescription: Test lifecycle\n---\n\n# Skill\n")
        self.assertEqual(repo.check(self.root)["errors"], [])
        (self.root / ".agents/skills/meos-intent/SKILL.md").unlink()
        self.assertIn("Expected the five local MEOS lifecycle skills", repo.check(self.root)["errors"])


if __name__ == "__main__":
    unittest.main()


class PlainLanguageTests(unittest.TestCase):
    """Simplified Technical English rules for the pages people read."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {"pages": ["docs/*.md"], "banned_words": {r"\bpackets?\b": "task record"},
                       "banned_exempt": ["docs/glossary.md"], "max_sentence_words": 25, "max_step_words": 20,
                       "max_paragraph_sentences": 6}

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def errors(self, content, path="docs/page.md"):
        return repo.plain_language_errors(self.root, self.write(path, content), self.config)

    def test_clean_page_passes(self):
        text = ("# Title\n\nThe site shows the grid. A clock replays the day.\n\n"
                "1. Open the page.\n2. Save a decision.\n\n| Word | Meaning |\n|---|---|\n| Grid | The network. |\n")
        self.assertEqual([], self.errors(text))

    def test_long_sentence_and_long_step_are_reported(self):
        long = " ".join(["word"] * 26) + "."
        self.assertIn("26 words", self.errors(long + "\n")[0])
        step = "1. " + " ".join(["word"] * 21) + ".\n"
        self.assertIn("limit 20", self.errors(step)[0])

    def test_passive_voice_banned_words_and_punctuation(self):
        found = self.errors("The packet was written by the team; it is done — fine. See e.g. this.\n")
        rules = " ".join(found)
        for needle in ("banned word 'packet'", "passive voice", "dash or semicolon", "Latin abbreviation"):
            self.assertIn(needle, rules)

    def test_code_links_and_fences_are_ignored_and_glossary_is_exempt(self):
        text = "Run `packet tool`. Read the [packet](x.md).\n\n```sh\npacket was done\n```\n"
        found = self.errors(text)
        self.assertEqual(1, len(found), found)
        self.assertIn("banned word 'packet'", found[0])
        self.assertEqual([], self.errors("The packet is the task record.\n", "docs/glossary.md"))

    def test_a_false_passive_match_does_not_hide_a_later_real_one(self):
        found = self.errors("The desk is open and the record is stored.\n")
        self.assertEqual(1, len(found), found)
        self.assertIn("passive voice 'is stored'", found[0])
        self.assertEqual([], self.errors("The desk is open when the clock starts.\n"))

    def test_sentence_may_end_with_a_closing_quote(self):
        text = 'It reads: "' + " ".join(["word"] * 20) + '." Then a second sentence follows here.\n'
        self.assertEqual([], self.errors(text))

    def test_paragraph_limit(self):
        text = " ".join(["One short sentence."] * 7) + "\n"
        self.assertIn("7 sentences", self.errors(text)[0])

    def test_pages_glob_selects_files(self):
        self.write("docs/a.md", "x\n")
        self.write("docs/sub/b.md", "x\n")
        pages = repo.plain_language_pages(self.root, {"pages": ["docs/*.md", "docs/sub/*.md"]})
        self.assertEqual(["a.md", "b.md"], [p.name for p in pages])


class ReviewerOutputIsSkipped(unittest.TestCase):
    """The ignored .meos/reviews folder holds reviewer output with absolute path:line links; the walk skips it."""

    def test_meos_reviews_is_skipped_and_other_reviews_folders_are_not(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".meos" / "reviews").mkdir(parents=True)
            (root / ".meos" / "reviews" / "r.md").write_text("[x](/absolute/nowhere.md:3)\n", encoding="utf-8")
            (root / ".meos" / "lifecycle.md").write_text("kept\n", encoding="utf-8")
            (root / "docs" / "work" / "reviews").mkdir(parents=True)
            (root / "docs" / "work" / "reviews" / "T-1.md").write_text("kept\n", encoding="utf-8")
            seen = {str(path.relative_to(root)) for path in repo.repository_files(root)}
        self.assertNotIn(".meos/reviews/r.md", seen)
        self.assertIn(".meos/lifecycle.md", seen)
        self.assertIn("docs/work/reviews/T-1.md", seen)

