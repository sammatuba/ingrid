#!/usr/bin/env python3
"""Offline, stdlib-only documentation routing and repository integrity checks."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PHASES = ("strategy", "intent", "implement", "review")
STATUSES = ("draft", "ready", "in_progress", "awaiting_input", "complete")
SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", ".delta", ".local"}


def local_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError(f"Expected a repository-relative path: {value!r}")
    path = (root / value).resolve()
    if Path(value).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path leaves the repository: {value}")
    if not path.is_file():
        raise ValueError(f"Missing file: {value}")
    return path


def read_json(root: Path, value: str) -> dict:
    data = json.loads(local_path(root, value).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected an object: {value}")
    return data


def validate_handoff(root: Path, data: dict, packet: bool = False) -> None:
    if data.get("version") != 1 or data.get("phase") not in PHASES or data.get("status") not in STATUSES:
        raise ValueError("Invalid handoff version, phase or status")
    key = "id" if packet else "work_id"
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", data.get(key, "")):
        raise ValueError(f"Invalid {key}")
    if not isinstance(data.get("next_action"), str) or not data["next_action"].strip():
        raise ValueError("Handoff needs an exact next_action")
    blockers = data.get("blockers")
    if not isinstance(blockers, list) or any(not isinstance(b, str) or not b.strip() for b in blockers):
        raise ValueError("blockers must be a list of nonempty descriptions")
    if blockers and data["status"] in ("ready", "complete"):
        raise ValueError("A blocked handoff cannot be ready or complete")
    if data["status"] == "awaiting_input" and not blockers:
        raise ValueError("awaiting_input must describe the missing input")
    if packet:
        if not re.fullmatch(r"[0-9a-f]{7,40}", data.get("base_commit", "")):
            raise ValueError("work.json needs its starting Git revision")
        artifacts = data.get("artifacts")
        if not isinstance(artifacts, dict) or not artifacts or any(k not in PHASES for k in artifacts):
            raise ValueError("artifacts must map lifecycle phases to files")
        if data["phase"] not in artifacts:
            raise ValueError("The current phase needs a durable artifact")
        if data["phase"] in ("implement", "review") and "intent" not in artifacts:
            raise ValueError("Implementation/review needs an intent artifact")
        if data["status"] == "complete" and data["phase"] == "review" and "implement" not in artifacts:
            raise ValueError("Completed review needs implementation evidence")
        paths = list(artifacts.values())
    else:
        paths = data.get("references")
        if not isinstance(paths, list) or not paths:
            raise ValueError("Default handoff needs references")
    for value in paths:
        local_path(root, value)


def route(root: Path, task: str, work: str | None = None) -> dict:
    config = read_json(root, "docs/routes.json")
    task = config.get("aliases", {}).get(task, task)
    if task not in config["routes"]:
        raise ValueError(f"Unknown route: {task}. Choose: {', '.join(config['routes'])}")
    paths = list(config["bootstrap"]) + list(config["routes"][task])
    if work and task not in PHASES:
        raise ValueError("--work applies to lifecycle routes only")
    if task in PHASES:
        if work:
            manifest = work if work.endswith(".json") else f"{work.rstrip('/')}/work.json"
            data = read_json(root, manifest)
            validate_handoff(root, data, packet=True)
            phases = {"strategy": ("strategy",), "intent": ("strategy", "intent"),
                      "implement": ("intent", "implement"), "review": ("intent", "implement", "review")}[task]
            paths += [manifest] + [data["artifacts"][p] for p in phases if p in data["artifacts"]]
        else:
            manifest = "docs/work/current.json"
            data = read_json(root, manifest)
            validate_handoff(root, data)
            paths += [manifest] + data["references"]
    paths = list(dict.fromkeys(paths))
    characters = sum(len(local_path(root, p).read_text(encoding="utf-8-sig")) for p in paths)
    return {"route": task, "files": paths, "estimated_tokens": (characters + 3) // 4,
            "estimate_method": "characters / 4; not a tokenizer measurement"}


def markdown_body(text: str) -> str:
    """Ignore fenced examples, including tildes and backtick fences longer than three."""
    lines = []
    fence = None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return "\n".join(lines)


def anchors(text: str) -> set[str]:
    seen: dict[str, int] = {}
    values = set(re.findall(r'<a\s+(?:[^>]*?\s)?(?:id|name)=["\']([^"\']+)', text))
    for heading in re.findall(r"^#{1,6}\s+(.+?)(?:\s+#+)?$", markdown_body(text), re.M):
        slug = re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        values.add(f"{slug}-{count}" if count else slug)
    return values


def markdown_errors(root: Path, path: Path) -> tuple[list[str], int]:
    text = markdown_body(path.read_text(encoding="utf-8-sig"))
    errors = []
    count = 0
    # This repository uses inline Markdown links. Also cover reference-link definitions.
    targets = re.findall(r"\]\((<[^>]+>|[^\s)]+)(?:\s+\"[^\"]*\")?\)", text)
    targets += re.findall(r"^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)", text, re.M)
    for value in targets:
        value = value.strip("<>")
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc:
            continue
        count += 1
        target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path.resolve()
        label = f"{path.relative_to(root).as_posix()}: {value}"
        if not target.is_relative_to(root.resolve()):
            errors.append(f"Link leaves repository: {label}")
        elif not target.exists():
            errors.append(f"Broken local link: {label}")
        elif parsed.fragment and target.suffix == ".md":
            if unquote(parsed.fragment) not in anchors(target.read_text(encoding="utf-8-sig")):
                errors.append(f"Missing heading target: {label}")
    return errors, count


PLAIN_DEFAULTS = {"max_sentence_words": 25, "max_step_words": 20, "max_paragraph_sentences": 6}
PARTICIPLES = ("built", "made", "done", "kept", "held", "left", "sent", "shown", "given", "taken", "written", "read",
               "set", "put", "run", "cut", "found", "met", "told", "said", "chosen", "drawn", "known", "seen", "spent",
               "lost", "paid", "sold", "bought", "brought", "caught", "taught", "thought", "begun", "got", "led", "fed",
               "hit", "split", "spread", "won", "meant", "understood", "hidden", "forbidden", "frozen", "broken")
NOT_PARTICIPLES = {"when", "then", "often", "even", "open", "seven", "eleven", "ten", "green", "golden", "keen",
                   "between", "again", "children", "kitchen", "men", "women", "queen", "screen", "oxygen", "sudden",
                   "wooden"}
PASSIVE = re.compile(r"\b(?:is|are|was|were|be|been|being|get|gets|got)\s+(?:\w+ly\s+)?(\w+ed|\w+en|"
                     + "|".join(PARTICIPLES) + r")\b", re.I)
SENTENCE_END = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"')\]]))\s+(?=[\"'(\[A-Z0-9])")


def plain_text(line: str) -> str:
    """Prose only: inline code, links, images, emphasis and HTML are removed from one Markdown line."""
    line = re.sub(r"<!--.*?-->", " ", line)
    line = re.sub(r"`[^`]*`", " X ", line)
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", line)
    line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
    line = re.sub(r"<[^>]+>", " ", line)
    line = re.sub(r"[*_]{1,3}(\S.*?\S|\S)[*_]{1,3}", r"\1", line)
    return re.sub(r"\s+", " ", line).strip()


def plain_blocks(text: str):
    """Yield (kind, text) blocks: heading, step, item, cell, paragraph."""
    paragraph: list[str] = []
    for raw in markdown_body(text).splitlines() + [""]:
        line = raw.strip()
        if not line or line.startswith("#") or re.match(r"^\s*([-*+]|\d+[.)])\s+", raw) or line.startswith("|"):
            if paragraph:
                yield "paragraph", " ".join(paragraph)
                paragraph = []
        if not line:
            continue
        if line.startswith("#"):
            yield "heading", plain_text(line.lstrip("#").strip())
        elif line.startswith("|"):
            if re.fullmatch(r"\|[\s:|-]+\|", line):
                continue
            for cell in line.strip("|").split("|"):
                if plain_text(cell):
                    yield "cell", plain_text(cell)
        elif re.match(r"^\s*\d+[.)]\s+", raw):
            yield "step", plain_text(re.sub(r"^\s*\d+[.)]\s+", "", raw))
        elif re.match(r"^\s*[-*+]\s+", raw):
            yield "item", plain_text(re.sub(r"^\s*[-*+]\s+", "", raw))
        else:
            paragraph.append(plain_text(raw))


def sentences(text: str) -> list[str]:
    return [s for s in SENTENCE_END.split(text) if s.strip()]


def plain_language_errors(root: Path, path: Path, config: dict) -> list[str]:
    """Simplified Technical English rules for the pages people read.

    Short sentences (25 words; 20 in a numbered step), short paragraphs, no passive voice, no banned
    words, no semicolons or dashes inside a sentence, no Latin abbreviations.
    """
    label = path.relative_to(root).as_posix()
    limits = {**PLAIN_DEFAULTS, **{k: v for k, v in config.items() if k in PLAIN_DEFAULTS}}
    banned = [(re.compile(pattern, re.I), replacement) for pattern, replacement in config.get("banned_words", {}).items()]
    exempt = label in config.get("banned_exempt", [])
    allowed_passive = {w.lower() for w in config.get("passive_allow", [])}
    errors = []

    def report(rule: str, text: str) -> None:
        errors.append(f"Plain language ({rule}): {label}: {text[:90]}")

    for kind, text in plain_blocks(path.read_text(encoding="utf-8-sig")):
        if not exempt:
            for pattern, replacement in banned:
                hit = pattern.search(text)
                if hit:
                    report(f"banned word '{hit.group(0)}', use '{replacement}'", text)
        if re.search(r"\b(?:e\.g\.|i\.e\.|etc\.|vs\.)", text):
            report("Latin abbreviation", text)
        if kind == "heading":
            continue
        if "—" in text or "–" in text or ";" in text:
            report("dash or semicolon", text)
        parts = sentences(text)
        if kind == "paragraph" and len(parts) > limits["max_paragraph_sentences"]:
            report(f"{len(parts)} sentences in one paragraph, limit {limits['max_paragraph_sentences']}", text)
        limit = limits["max_step_words"] if kind == "step" else limits["max_sentence_words"]
        for sentence in parts:
            words = len(sentence.split())
            if words > limit:
                report(f"{words} words in one sentence, limit {limit}", sentence)
            hit = next((m for m in PASSIVE.finditer(sentence) if m.group(1).lower() not in NOT_PARTICIPLES), None)
            if hit and hit.group(1).lower() not in allowed_passive:
                report(f"passive voice '{hit.group(0)}'", sentence)
    return errors


def plain_language_pages(root: Path, config: dict) -> list[Path]:
    pages: list[Path] = []
    for pattern in config.get("pages", []):
        pages.extend(sorted(p for p in root.glob(pattern) if p.is_file()))
    return pages


def repository_files(root: Path):
    for current, directories, files in os.walk(root):
        directories[:] = [d for d in directories if d not in SKIP and not (Path(current) / d).is_symlink()
                          and not (d == "reviews" and Path(current).name == ".meos")]  # ignored reviewer output
        for name in files:
            yield Path(current) / name


def check(root: Path) -> dict:
    errors = []
    files = list(repository_files(root))
    markdown = [p for p in files if p.suffix == ".md"]
    links = 0
    for path in markdown:
        found, count = markdown_errors(root, path)
        errors.extend(found)
        links += count
    bootstrap_words = 0
    try:
        config = read_json(root, "docs/routes.json")
        if config.get("version") != 1:
            raise ValueError("Unsupported route registry version")
        for task in config["routes"]:
            route(root, task)
        for alias, target in config.get("aliases", {}).items():
            if target not in config["routes"]:
                raise ValueError(f"Unknown alias target: {alias} -> {target}")
        bootstrap_words = sum(len(local_path(root, p).read_text(encoding="utf-8").split()) for p in config["bootstrap"])
        if bootstrap_words > config["bootstrap_word_budget"]:
            errors.append(f"Bootstrap exceeds word budget: {bootstrap_words} > {config['bootstrap_word_budget']}")
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(f"Routing: {exc}")
    try:
        plain = read_json(root, "docs/routes.json").get("plain_language", {})
        for path in plain_language_pages(root, plain):
            errors.extend(plain_language_errors(root, path, plain))
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(f"Plain language: {exc}")
    for path in (root / "docs/work").glob("*/work.json"):
        try:
            validate_handoff(root, json.loads(path.read_text(encoding="utf-8")), packet=True)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    skills = list((root / ".agents/skills").glob("*/SKILL.md"))
    required_skills = {f"meos-{phase}" for phase in (*PHASES, "wrapup")}
    if not required_skills.issubset({path.parent.name for path in skills}):
        errors.append("Expected the five local MEOS lifecycle skills")
    for path in skills:
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not match:
            errors.append(f"Missing skill frontmatter: {path.relative_to(root)}")
            continue
        fields = dict(re.findall(r"^(name|description):\s*(.+)$", match.group(1), re.M))
        if fields.get("name") != path.parent.name or not fields.get("description"):
            errors.append(f"Invalid skill identity/description: {path.relative_to(root)}")
        if len(text.split()) > 650:
            errors.append(f"Skill exceeds 650-word loading budget: {path.relative_to(root)}")
    manifest = root / "docs/engineering/migrations/platform-layout-2026-10-03.json"
    if manifest.exists():
        for item in json.loads(manifest.read_text(encoding="utf-8"))["files"]:
            try:
                local_path(root, item["to"])
            except ValueError as exc:
                errors.append(str(exc))
    return {"markdown_files": len(markdown), "local_links": links, "skills": len(skills),
            "bootstrap_words": bootstrap_words, "errors": errors}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    routing = commands.add_parser("route", help="Print a minimal context packet without loading its contents")
    routing.add_argument("task")
    routing.add_argument("--work", help="Explicit repo-relative work folder or work.json; overrides default")
    routing.add_argument("--json", action="store_true")
    checking = commands.add_parser("check", help="Check local links, routing, handoffs, plain language and skill structure")
    checking.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = route(ROOT, args.task, args.work) if args.command == "route" else check(ROOT)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"Repository check failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    elif args.command == "route":
        print(f"Route: {result['route']} (~{result['estimated_tokens']} tokens; characters/4 estimate)")
        print("\n".join(result["files"]))
    else:
        print(f"Checked {result['markdown_files']} Markdown files, {result['local_links']} local links, "
              f"{result['skills']} skills; bootstrap {result['bootstrap_words']} words.")
        print("\n".join(result["errors"]) if result["errors"] else "PASS")
    return int(bool(result.get("errors")))


if __name__ == "__main__":
    raise SystemExit(main())
