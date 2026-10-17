#!/usr/bin/env python3
"""Mirror a repository's docs/ into the site repository checkout (stdlib only).

Used by .github/workflows/sync-docs.yml. Replaces the former bash/rsync steps.

  sync_docs.py copy   : <docs>/[<lang>/]site.md -> site/content/projects/[<lang>/]<name>.md
  sync_docs.py mirror : user-facing <docs>/**/*.md -> site/content/docs/<name>/ (+ locales)
  sync_docs.py push   : commit when content changed and push with rebase retries

Configuration comes from the environment (set by the workflow), never from argv.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

INTERNAL = [
    "research/", "research*.md", "qa/", "*audit*.md",
    "design/", "brand/", "assets/", "adr/", "notes/",
    "proposals/", "*proposal*.md",
    "plan*.md", "PLAN*.md", "todo*.md", "TODO*.md",
    "next*.md", "done*.md", "roadmap*.md", "ideas.md",
    "AGENTS.md", "CLAUDE.md", "agency.md",
    "sonarcloud-setup.md", "release.md", "release-*.md",
]


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def excluded(rel: str, is_dir: bool, patterns: list[str]) -> bool:
    """rsync-like exclude: no leading / matches at any depth, trailing / dirs only."""
    for pat in patterns:
        dir_only = pat.endswith("/")
        pat = pat.rstrip("/")
        if dir_only and not is_dir:
            continue
        if pat.startswith("/"):
            if fnmatch.fnmatchcase(rel, pat[1:]):
                return True
        elif "/" in pat:
            if fnmatch.fnmatchcase(rel, pat) or fnmatch.fnmatchcase(rel, "*/" + pat):
                return True
        elif fnmatch.fnmatchcase(rel.rsplit("/", 1)[-1], pat):
            return True
    return False


def select(src: Path, patterns: list[str]) -> set[str]:
    """Relative paths of the *.md files to publish (site.md at the root is a card)."""
    found: set[str] = set()
    for root, dirs, files in os.walk(src):
        base = Path(root).relative_to(src).as_posix()
        base = "" if base == "." else base + "/"
        dirs[:] = [d for d in dirs if not excluded(base + d, True, patterns)]
        for name in files:
            rel = base + name
            if rel == "site.md" or not name.endswith(".md"):
                continue
            if not excluded(rel, False, patterns):
                found.add(rel)
    return found


def mirror(src: Path, dest: Path, patterns: list[str], keep_top: set[str]) -> None:
    want = select(src, patterns) if src.is_dir() else set()
    dest.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(dest, topdown=True):
        base = Path(root).relative_to(dest).as_posix()
        base = "" if base == "." else base + "/"
        if base == "":
            dirs[:] = [d for d in dirs if d not in keep_top]
        for name in files:
            rel = base + name
            if rel not in want and rel != "_source.json":
                (dest / rel).unlink()
    for rel in sorted(want):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src / rel, target)
    for root, _dirs, _files in os.walk(dest, topdown=False):
        p = Path(root)
        if p != dest and not any(p.iterdir()) and p.relative_to(dest).parts[0] not in keep_top:
            p.rmdir()


def set_version(path: Path, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?\n)---\n", text, re.S)
    if not m:
        return
    fm = m.group(1)
    line = f'version: "{version}"\n'
    if re.search(r"^version:.*\n", fm, re.M):
        fm = re.sub(r"^version:.*\n", lambda _m: line, fm, count=1, flags=re.M)
    else:
        fm += line
    path.write_text(f"---\n{fm}---\n" + text[m.end():], encoding="utf-8")


def cmd_copy() -> int:
    docs, project = env("DOCS_DIR", "docs"), env("PROJECT")
    for lang in [""] + env("LOCALES").split():
        sub = f"{lang}/" if lang else ""
        src = Path(f"source/{docs}/{sub}site.md")
        dest = Path(f"site/content/projects/{sub}{project}.md")
        if not src.is_file():
            if not lang:
                print(f"::error::{docs}/site.md is missing")
                return 1
            dest.unlink(missing_ok=True)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        if env("REF_TYPE") == "tag":
            ref = env("REF_NAME")
            set_version(dest, ref[1:] if ref.startswith("v") else ref)
    return 0


def cmd_mirror() -> int:
    docs, project = env("DOCS_DIR", "docs"), env("PROJECT")
    locales = env("LOCALES").split()
    patterns = INTERNAL + [p.strip() for p in env("EXTRA_EXCLUDES").splitlines() if p.strip()]
    dest = Path(f"site/content/docs/{project}")
    # English mirror leaves the locale folders alone (excluded in, protected out).
    mirror(Path(f"source/{docs}"), dest, patterns + [f"/{x}/" for x in locales], set(locales))
    for lang in locales:
        src = Path(f"source/{docs}/{lang}")
        if src.is_dir():
            mirror(src, dest / lang, patterns, set())
        else:
            shutil.rmtree(dest / lang, ignore_errors=True)
    (dest / "_source.json").write_text(
        json.dumps({"repo": env("SOURCE"), "sha": env("SOURCE_SHA"), "ref": env("REF_NAME")}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


def git(*args: str, check: bool = True, cwd: str = "site") -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=check)


def cmd_push() -> int:
    project, branch = env("PROJECT"), env("SITE_BRANCH", "main")
    git("add", "-A", "--", "content/projects", f"content/docs/{project}")
    quiet = git("diff", "--cached", "--quiet", "--", ".", f":(exclude)content/docs/{project}/_source.json", check=False)
    if quiet.returncode == 0:
        print(f"content/projects/{project}.md and content/docs/{project}/ are already up to date")
        return 0
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("commit", "-m", f"content: sync {project} from {env('SOURCE')}@{env('SOURCE_SHA')[:7]} ({env('REF_NAME')})")
    for attempt in range(1, 6):
        if git("push", "origin", f"HEAD:{branch}", check=False).returncode == 0:
            print(f"pushed to {env('SITE_REPOSITORY')} {branch}")
            return 0
        print(f"push rejected (attempt {attempt}); rebasing onto the latest {branch}")
        time.sleep(attempt * 3)
        git("fetch", "origin", branch)
        git("rebase", f"origin/{branch}")
    print(f"::error::could not push to {env('SITE_REPOSITORY')} {branch} after 5 attempts")
    return 1


def main() -> int:
    cmds = {"copy": cmd_copy, "mirror": cmd_mirror, "push": cmd_push}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        print(__doc__, file=sys.stderr)
        return 2
    return cmds[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())
