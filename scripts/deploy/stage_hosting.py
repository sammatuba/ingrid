#!/usr/bin/env python3
"""Stage the grid page, its design files and the baked replay data as a Firebase Hosting tree.

PERF-5, option (a) of the performance intent: the first screen a judge sees is `/`, so the grid
page and the replay files it reads are served by Firebase Hosting's CDN instead of waiting for a
cold Cloud Run instance. This script assembles that tree under ``build/hosting`` from the same
two inputs the image is built from — the baked replay data (``build/grid-data``, company WESM
data that never enters Git or the public export) and the grid design files (``src/grid``) — at
the build-stamped paths PERF-1 introduced:

    build/hosting/index.html                     the grid page, stamp written into its URLs
    build/hosting/favicon.ico, favicon.svg, …    the InGRID icons and manifest (ROOT_FILES)
    build/hosting/grid/<stamp>/…                 the page's JS, CSS and fonts, byte for byte
    build/hosting/grid-data/<stamp>/…            every baked replay file, byte for byte

It also writes the config the site is released with, beside the stage (``build/firebase.json``):
the template ``--config`` names (``scripts/deploy/firebase.json``) with the same build stamp
written into its stamped header rules. The immutable rules of the deployed config therefore name
``/grid/<stamp>/**`` and ``/grid-data/<stamp>/**`` — exactly the files this stage holds — and
never an unversioned name, another build's stamp, or a route the single ``"**"`` rewrite proxies
to Cloud Run; ``public`` names the stage from the directory holding the generated config, which
is where firebase-tools resolves it. ``deploy.sh`` releases Hosting with that generated config,
never with the template: a template alone cannot name the stamp.

``<stamp>`` is the 16-hex build stamp ``src.api.build_stamp`` derives from exactly those two
trees when the application (or the image built from this work tree) computes it; this module
re-derives it with the same walk — every file's label, relative name and content digest, in
sorted order, the image's nested data copy counted once — and a test pins the two derivations
together. So the page Hosting serves names the same versioned URLs the application would serve,
and every one of them is a staged file.

What it refuses (exit 2, nothing written):

* ``build/grid-data`` missing or holding no file — the acceptance's own refusal: there is no
  replay data to publish, and a stage without it would serve a page that cannot draw.
* a design file the page needs missing from ``src/grid``, or a ``src/grid/grid-data`` the image
  layout would derive a different stamp around (the checkout is not the image).
* a staged tree whose own derivation does not reproduce the stamp of its inputs — a file added,
  renamed or left out between the walk and the write.
* a ``--out`` (or the generated config) inside a Git work tree that Git would track: the stage
  carries company data, so both belong with the baked tree in an ignored path (the orchestrator
  owns ``.gitignore``).
* a generated config inside the stage (Hosting publishes every file published there), over the
  template it is generated from, or a template naming no stamped header rule.
* an existing stage or config that ``--check`` finds holding anything but the one stamp's listed
  files and the config regenerated from them.

It never reaches the network, never reads a credential and never writes outside ``--out`` and
``--config-out``.

Commands::

    stage_hosting.py [--data DIR] [--grid DIR] [--out DIR] [--config FILE] [--config-out FILE]
                     [--json]
    stage_hosting.py --check [...]      validate an existing stage and config, write nothing

``--out`` defaults to the directory ``--config`` names (``hosting.public``, resolved against the
directory holding the config file — firebase-tools resolves it that way, its `projectDir` is the
directory of firebase.json); ``--config-out`` defaults to ``firebase.json`` beside the stage.
Exit codes: 0 staged (or valid), 2 usage or refusal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "scripts" / "deploy" / "firebase.json"
DEFAULT_DATA = ROOT / "build" / "grid-data"
DEFAULT_GRID = ROOT / "src" / "grid"

# The design files the application serves (src/api/__init__.py GRID_FILES) and the font name
# rule (FONT_NAME): the stager's copy is the same allow-list, and tests pin them equal.
GRID_FILES = ("index.html", "event.html", "event.css", "event.js", "event-api.js",
              "grid.css", "grid.js", "explain.html", "explain.css", "explain.js",
              # DESK-3: the outlooks page, the archive's own surface.
              "outlooks.html", "outlooks.css", "outlooks.js",
              # DESK-5: the register page, the assumption register's own surface.
              "register.html", "register.css", "register.js",
              # ROUTES-1: the four pages the page briefs build (/models, /work, /map, /ask),
              # shipped as shells so the stage passes before the briefs land.
              "models.html", "models.css", "models.js",
              "work.html", "work.css", "work.js",
              "map.html",
              "ask.html", "ask.css", "ask.js",
              # UX-1: the command bar every page but /ask loads through shell.js.
              "command.js", "command.css", "ui.css", "ui.js",
              "projectmap.css", "reading.js",  # PP-B4
              "assets.html", "asset.html", "asset.css", "asset.js",
              # ATG-8: ATG-4's catalog page, ATG-5's briefing/findings panel and ATG-6's map
              # canvas, which the grid page loads; the stage carries every file the served pages
              # reference.
              "catalog.html", "catalog.css", "catalog.js", "briefs.css", "briefs.js",
              "map.css", "map.js",
              # The alerts page's design files and the vendored Firebase JS SDK it loads.
              "alerts.html", "alerts.css", "alerts.js",
              "firebase-app-compat.js", "firebase-auth-compat.js",
              # The working paper's page and stylesheet (/paper, scripts/docs/build_paper.py).
              "paper.html", "paper.css",
              "shell.css", "shell.js", "outages.css", "outages.js",
              # ericka-desk slice 8: the journal page and its reusable "Add to journal" box.
              "journal.html", "journal.css", "journal.js", "journal-box.js",
              # ericka-desk slice 3: the dashboard overview.
              "overview.js", "overview.css",
              # ericka-desk slice 7: the event desk.
              "event-desk.js", "event-desk.css", "dash-alerts.js", "dash-map.js", "dashboard.css",
              "notices.html", "notices.js", "notices.css",
              # ericka-desk: the alert settings page (/settings), driven by alerts.js.
              "settings.html", "settings.css",
              # ericka-desk: an alert's own page (/alert/<alert key>), built from the replay on request.
              "spike.html", "spike.js", "spike.css",
              # BOOK-3's book page (/book, DOCK-5): the synthetic book's exposure.
              "book.html", "book.css", "book.js",
              # "How we got this": the data-flow dialog behind the "?" on card headers.
              "flow.js", "flow.css",
              # InGRID brand (docs/brand/README.md): the mark, the logo and the root icons.
              "ingrid-mark.svg", "ingrid-logo.svg",
              "favicon.ico", "favicon.svg", "apple-touch-icon.png", "icon-192.png",
              "icon-512.png", "icon-maskable-512.png", "site.webmanifest")
# src/api/__init__.py BRAND_ROOT_FILES: the icons and manifest a browser asks for at the site
# root. Each is also staged at the root, byte for byte the design file of the same name, so
# Hosting answers them without a Cloud Run hop; tests pin the two lists equal.
ROOT_FILES = ("favicon.ico", "favicon.svg", "apple-touch-icon.png", "icon-192.png",
              "icon-512.png", "icon-maskable-512.png", "site.webmanifest")
FONT_NAME = re.compile(r"[a-z0-9][a-z0-9._-]*\.woff2\Z")
# src/api/__init__.py STAMP_SIZE / STAMP_TOKEN: the page carries the token where the stamp goes.
STAMP_SIZE = 16
STAMP_TOKEN = "__NOWCAST_STAMP__"
STAMP_SHAPE = re.compile(r"[0-9a-f]{%d}\Z" % STAMP_SIZE)
FAMILIES = ("grid", "grid-data")
# The generated config is written beside the stage under this name unless --config-out says
# otherwise (build/hosting -> build/firebase.json): firebase-tools resolves `hosting.public`
# against the directory holding the config file, so a config beside the stage names it with a
# plain relative path and the release cannot publish a different directory than the stage wrote.
CONFIG_NAME = "firebase.json"


class StageError(Exception):
    """A refused input, destination or stage; the message is the whole refusal."""


# ------------------------------------------------------------------ the stamp and the inputs

def build_stamp(data_dir, grid_dir) -> str:
    """The content-derived build stamp, derived exactly as ``src.api.build_stamp`` derives it.

    Every file under the data directory and under the grid directory contributes its label,
    relative name and content digest, in sorted order, so the stamp moves when any byte of a
    replay file, a page, a script, a stylesheet or a font moves. A resolved path met twice is
    counted once — the image keeps the baked data inside ``src/grid``, where the walk would meet
    it again — so the image layout and the ``build/grid-data`` tree derive the same stamp. A
    root that is not there contributes nothing. DATA-2: the bake manifest (``manifest.json`` at
    the data root) is the one file left out, as ``src.api.build_stamp`` leaves it out: it
    records this stamp, so it cannot be part of it. It is still staged byte for byte.
    """
    digest = hashlib.sha256()
    seen = set()
    for label, root in (("data", data_dir), ("grid", grid_dir)):
        root = Path(root)
        if not root.is_dir():
            continue
        for path in sorted(entry for entry in root.rglob("*") if entry.is_file()):
            resolved = path.resolve()
            # DATA-2: the bake manifest at the data root names this stamp, so it cannot be part
            # of it; it is marked seen, so the image's copy inside src/grid is not counted either.
            if label == "data" and path.relative_to(root).as_posix() == "manifest.json":
                seen.add(resolved)
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            digest.update(label.encode("ascii"))
            digest.update(b"\0")
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()[:STAMP_SIZE]


def design_files(grid_dir) -> dict:
    """``relative name -> path`` for the files the stage copies from the design tree.

    Every file under ``src/grid`` is staged, not only the names the application serves: the
    build stamp counts every file of that tree — the vendored fonts' licence texts beside them —
    so a stage carrying less would derive a stamp the image does not use. The pages, scripts,
    stylesheets and at least one font must be there, or the staged page could not draw.
    """
    root = Path(grid_dir)
    if not root.is_dir():
        raise StageError("refusing: the grid design tree %s is not there" % root)
    if (root / "grid-data").exists():
        raise StageError(
            "refusing: %s holds a baked-data copy (src/grid/grid-data): the image derives its "
            "stamp with that copy counted once, this work tree would count it twice, so a stage "
            "built here could not name the image's files. Build the image from this tree and "
            "stage from build/grid-data, with src/grid carrying no baked copy." % root)
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise StageError("refusing: cannot read %s: %s" % (path, exc)) from None
        if root.resolve() not in resolved.parents:
            raise StageError("refusing: %s resolves outside %s; the stage never follows a file "
                             "out of its design tree" % (path, root))
        files[path.relative_to(root).as_posix()] = resolved
    for name in GRID_FILES:
        if name not in files:
            raise StageError("refusing: the grid design file %s is not in %s; the staged page "
                             "would not draw" % (name, root))
    if not any(name.startswith("fonts/") and FONT_NAME.fullmatch(name[6:]) for name in files):
        raise StageError("refusing: %s vendors no font; the page's faces would 404" % root)
    return files


def replay_files(data_dir) -> dict:
    """``relative name -> resolved path`` for every baked replay file, or a refusal."""
    root = Path(data_dir)
    if not root.is_dir():
        raise StageError("refusing: the baked replay data is not in %s; run scripts/grid/"
                         "build_data.py first (it writes build/grid-data)" % root)
    base = root.resolve(strict=True)
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise StageError("refusing: cannot read %s: %s" % (path, exc)) from None
        if resolved != base and base not in resolved.parents:
            raise StageError("refusing: %s resolves outside %s; the stage never follows a file "
                             "out of its data directory" % (path, base))
        files[path.relative_to(root).as_posix()] = resolved
    if not files:
        raise StageError("refusing: %s holds no replay file; the page would have nothing to "
                         "draw" % root)
    return files


def grid_page(grid_dir, stamp: str) -> bytes:
    """The served page: the source page with the build stamp written into every token."""
    source = (Path(grid_dir) / "index.html").read_bytes()
    token = STAMP_TOKEN.encode("ascii")
    if token not in source:
        raise StageError("refusing: src/grid/index.html carries no %s token; the staged page "
                         "could not name this build's files" % STAMP_TOKEN)
    return source.replace(token, stamp.encode("ascii"))


def stage_tree(stamp: str, assets: dict, data: dict, page: bytes) -> dict:
    """The stage as ``relative name -> bytes source``: the page, then one stamped family each.

    The mapping is the whole contract of the stage: exactly the grid page and the root icons
    (ROOT_FILES) at the root, every design file under ``grid/<stamp>/`` and every replay file
    under ``grid-data/<stamp>/``, each byte for byte the file it comes from.
    """
    tree = {"index.html": page}
    for name in ROOT_FILES:
        tree[name] = assets[name]
    for name, path in assets.items():
        tree["grid/%s/%s" % (stamp, name)] = path
    for name, path in data.items():
        tree["grid-data/%s/%s" % (stamp, name)] = path
    return tree


# ------------------------------------------------------------------------- writing and checking

def git_toplevel(anchor: Path):
    """The work-tree root holding ``anchor``, or ``None`` when there is none."""
    try:
        result = subprocess.run(["git", "-C", str(anchor), "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True)
    except OSError:
        return None
    return Path(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else None


def git_ignored(root: Path, path: Path) -> bool:
    result = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", str(path)],
                            capture_output=True)
    return result.returncode == 0


def existing_ancestor(path: Path) -> Path:
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def refuse_tracked_out(out: Path, what: str = "the staged replay data") -> None:
    """A stage or deploy artifact inside a Git work tree must be in an ignored path."""
    top = git_toplevel(existing_ancestor(out))
    if top is not None and not git_ignored(top, out):
        raise StageError(
            "refusing: %s is inside the Git work tree %s and is not ignored; %s would be "
            "committed by `git add -A`. Add the directory to .gitignore (the orchestrator owns "
            "that file) or write it elsewhere." % (out, top, what))


def stage_inventory(out: Path):
    """``(stamp, {relative name: path})`` of a stage, or a refusal naming what is wrong.

    The layout is the contract: ``index.html``, the root icons and one stamp-named directory per
    family, each holding files only. Anything else — a second stamp, a loose file, a missing
    page — is a stage this release must not publish.
    """
    root = Path(out)
    if not root.is_dir():
        raise StageError("refusing: there is no stage in %s; run this script without --check "
                         "before releasing Hosting" % root)
    top = sorted(entry.name for entry in root.iterdir())
    if top != sorted(("grid", "grid-data", "index.html") + ROOT_FILES):
        raise StageError("refusing: %s holds %s; a stage is index.html, the root icons and one "
                         "stamped grid/ and grid-data/ directory" % (root, top))
    stamps, files = [], {name: root / name for name in ("index.html",) + ROOT_FILES}
    for family in FAMILIES:
        versions = sorted(entry for entry in (root / family).iterdir())
        named = [entry for entry in versions if entry.is_dir() and STAMP_SHAPE.match(entry.name)]
        if len(versions) != 1 or not named or named[0] != versions[0]:
            raise StageError("refusing: %s/%s holds %s; exactly one stamp-named directory is "
                             "staged" % (root, family, sorted(entry.name for entry in versions)))
        stamp_dir = versions[0]
        stamps.append(stamp_dir.name)
        for path in sorted(stamp_dir.rglob("*")):
            if path.is_dir():
                continue
            files["%s/%s/%s" % (family, stamp_dir.name, path.relative_to(stamp_dir).as_posix())] = path
    if stamps[0] != stamps[1]:
        raise StageError("refusing: %s names two builds (grid %s, grid-data %s); the page and "
                         "its data must come from one" % (root, stamps[0], stamps[1]))
    return stamps[0], files


def stage(out: Path, data_dir, grid_dir, template=DEFAULT_CONFIG, config_out=None) -> dict:
    """Assemble the stage and the config this build deploys, then put both in place.

    The write goes into a temporary directory beside ``out`` and is moved over it only after the
    staged tree reproduces its inputs' stamp, so a refused or interrupted run leaves the
    previous stage (or none) and never a half-published one. The generated config is written
    after the stage is in place, from the same stamp and naming that stage; ``--check`` reads
    both back, so a config left behind by an interrupted run is refused rather than released.
    """
    out = Path(out)
    config_out = Path(config_out) if config_out is not None else out.parent / CONFIG_NAME
    stamp = build_stamp(data_dir, grid_dir)
    assets = design_files(grid_dir)
    data = replay_files(data_dir)
    page = grid_page(grid_dir, stamp)
    tree = stage_tree(stamp, assets, data, page)
    refuse_tracked_out(out)
    refuse_config_out(config_out, template, out)
    if out.exists() and not out.is_dir():
        raise StageError("refusing: %s exists and is not a directory" % out)
    config = effective_config(template, stamp, out, config_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=out.name + ".staging-", dir=out.parent))
    try:
        for name, source in sorted(tree.items()):
            target = temporary / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(source, bytes):
                target.write_bytes(source)
            else:
                shutil.copyfile(source, target)
        derived = build_stamp(temporary / "grid-data" / stamp, temporary / "grid" / stamp)
        if derived != stamp:
            raise StageError(
                "refusing: the staged tree derives %s, not %s: a file of %s or %s was added, "
                "renamed or left out between the stamp and the write; nothing is released"
                % (derived, stamp, data_dir, grid_dir))
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    if out.exists():
        shutil.rmtree(out)
    temporary.rename(out)
    write_config(config_out, config)
    return {"stamp": stamp, "out": str(out), "config": str(config_out), "files": len(tree),
            "replay": len(data), "design": len(assets),
            "staged": sorted(tree)}


def check(out: Path, data_dir, grid_dir, template=DEFAULT_CONFIG, config_out=None) -> dict:
    """Validate an existing stage and its generated config against these inputs; write nothing."""
    out = Path(out)
    config_out = Path(config_out) if config_out is not None else out.parent / CONFIG_NAME
    stamp, files = stage_inventory(out)
    expected_stamp = build_stamp(data_dir, grid_dir)
    assets, data = design_files(grid_dir), replay_files(data_dir)
    expected = stage_tree(expected_stamp, assets, data, grid_page(grid_dir, expected_stamp))
    if stamp != expected_stamp:
        raise StageError("refusing: %s names build %s; the data in %s and %s derives %s; stage "
                         "again" % (out, stamp, data_dir, grid_dir, expected_stamp))
    missing = sorted(set(expected) - set(files))
    extra = sorted(set(files) - set(expected))
    if missing or extra:
        raise StageError("refusing: %s does not hold this build's files (missing: %s; not "
                         "staged by this build: %s)" % (out, missing or "none", extra or "none"))
    for name, source in sorted(expected.items()):
        wanted = source if isinstance(source, bytes) else Path(source).read_bytes()
        if files[name].read_bytes() != wanted:
            raise StageError("refusing: %s/%s differs from the file it was staged from; stage "
                             "again" % (out, name))
    expected_config = effective_config(template, stamp, out, config_out)
    try:
        present = config_out.read_bytes()
    except OSError as exc:
        raise StageError("refusing: there is no generated config in %s (%s); run this script "
                         "without --check before releasing Hosting" % (config_out, exc)) from None
    if present != expected_config:
        raise StageError(
            "refusing: %s is not the config %s and %s derive for build %s; the config is "
            "regenerated at staging time, so this file is stale, edited or another build's; "
            "stage again" % (config_out, out, template, stamp))
    return {"stamp": stamp, "out": str(out), "config": str(config_out), "files": len(files),
            "replay": len(data), "design": len(assets), "staged": sorted(files)}


# -------------------------------------------------------------------------------------- config

def load_template(config_path) -> dict:
    """The Hosting config template, parsed; every refusal names the file."""
    path = Path(config_path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StageError("refusing: cannot read the Hosting config %s: %s" % (path, exc)) from None
    hosting = document.get("hosting") if isinstance(document, dict) else None
    if not isinstance(hosting, dict):
        raise StageError("refusing: %s holds no hosting object; there is nothing for the site "
                         "to publish" % path)
    return document


def config_public_dir(config_path) -> Path:
    """The directory the template's ``hosting.public`` names, resolved as firebase-tools does.

    ``hosting.public`` is relative to the directory holding firebase.json: the CLI's project
    root is that directory when ``--config`` names the file (its `detectProjectRoot`, then
    `projectPath.resolveProjectPath` for the public value), so this is the stage's default
    ``--out`` and the release's own commands resolve the same way.
    """
    path = Path(config_path)
    public = load_template(path)["hosting"].get("public")
    if not isinstance(public, str) or not public.strip():
        raise StageError("refusing: %s names no hosting \"public\" directory; there is nothing "
                         "for the site to publish" % path)
    return (path.resolve().parent / public).resolve()


def stamped_rules(hosting: dict, path) -> list:
    """The template's header rules whose ``source`` carries the build-stamp token.

    These are the immutable rules: the stager writes this build's stamp where the token stands,
    so the deployed config matches exactly the staged files of this build — never an unversioned
    name, another build's stamp or a route the ``"**"`` rewrite proxies to Cloud Run. A template
    with no such rule is refused: the stage would be released with no cache class at all.
    """
    rules = hosting.get("headers")
    if rules is None:
        rules = []
    if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
        raise StageError("refusing: %s holds malformed \"headers\" rules" % path)
    stamped = [rule for rule in rules
               if isinstance(rule.get("source"), str) and STAMP_TOKEN in rule["source"]]
    if not stamped:
        raise StageError("refusing: %s names no header rule carrying %s; the generated config "
                         "would leave the staged files with no cache class" % (path, STAMP_TOKEN))
    return stamped


def relative_public(stage_dir, config_out) -> str:
    """The stage as firebase-tools resolves ``hosting.public``, from the generated config's dir."""
    return Path(os.path.relpath(Path(stage_dir).resolve(),
                                Path(config_out).resolve().parent)).as_posix()


def effective_config(template, stamp: str, stage_dir, config_out) -> bytes:
    """The Hosting config this build deploys, as bytes.

    The template with the build stamp written into its stamped header rules — so the immutable
    rules match exactly ``/grid/<stamp>/**`` and ``/grid-data/<stamp>/**``, the files the stage
    holds, and nothing an unversioned name, another build's stamp or a Cloud Run route answers —
    and its ``public`` naming the stage from the directory holding this config. Deterministic
    for a given (template, stamp, destination), so ``--check`` can regenerate and compare it.
    """
    path = Path(template)
    document = load_template(path)
    hosting = document["hosting"]
    for rule in stamped_rules(hosting, path):
        rule["source"] = rule["source"].replace(STAMP_TOKEN, stamp)
    hosting["public"] = relative_public(stage_dir, config_out)
    text = json.dumps(document, indent=2) + "\n"
    if STAMP_TOKEN in text:
        raise StageError("refusing: %s carries %s outside a header rule's source; the token "
                         "would be deployed verbatim" % (path, STAMP_TOKEN))
    return text.encode("utf-8")


def refuse_config_out(config_out, template, stage) -> None:
    """The generated config sits beside the stage: never inside it, never over the template."""
    resolved = Path(config_out).resolve()
    if resolved == Path(template).resolve():
        raise StageError("refusing: the generated config %s is the template it is generated "
                         "from; write it beside the stage instead" % config_out)
    stage_resolved = Path(stage).resolve()
    if resolved == stage_resolved or stage_resolved in resolved.parents:
        raise StageError(
            "refusing: %s is inside the stage %s; Hosting publishes every file staged there, and "
            "the config is not part of the site" % (config_out, stage))
    refuse_tracked_out(Path(config_out), "the generated Hosting config")


def write_config(config_out, content: bytes) -> None:
    """Write the generated config into place atomically, or refuse."""
    path = Path(config_out)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".writing",
                                             dir=path.parent)
    except OSError as exc:
        raise StageError("refusing: cannot write the generated config %s: %s"
                         % (path, exc)) from None
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise StageError("refusing: cannot write the generated config %s: %s"
                         % (path, exc)) from None


# ---------------------------------------------------------------------------------------- main

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA,
                        help="the baked replay tree (default: build/grid-data)")
    parser.add_argument("--grid", type=Path, default=DEFAULT_GRID,
                        help="the grid design tree (default: src/grid)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help="the Hosting config template the generated config is built from; its "
                             "\"public\" names the stage when --out is not given (default: "
                             "scripts/deploy/firebase.json)")
    parser.add_argument("--config-out", type=Path, default=None,
                        help="write the effective config for this build here (default: "
                             "firebase.json beside the stage)")
    parser.add_argument("--out", type=Path, default=None,
                        help="stage here (default: the directory --config publishes)")
    parser.add_argument("--check", action="store_true",
                        help="validate an existing stage and config against these inputs; write "
                             "nothing")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    try:
        out = args.out if args.out is not None else config_public_dir(args.config)
        config_out = (args.config_out if args.config_out is not None
                      else Path(out).parent / CONFIG_NAME)
        if args.check:
            report = check(out, args.data, args.grid, args.config, config_out)
        else:
            report = stage(out, args.data, args.grid, args.config, config_out)
    except StageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.check:
        print("OK: %s holds %s files of build %s (%s replay files, %s design files); %s is the "
              "config this build deploys"
              % (report["out"], report["files"], report["stamp"], report["replay"],
                 report["design"], report["config"]))
    else:
        print("staged %s files under %s for build %s (%s replay files, %s design files); config "
              "%s"
              % (report["files"], report["out"], report["stamp"], report["replay"],
                 report["design"], report["config"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
