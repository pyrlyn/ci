#!/usr/bin/env python3
"""Fail when a changed workflow file pins pyrlyn/ci to anything but `main`.

Callers must write `uses: pyrlyn/ci/<path>@main`. A commit SHA or a tag there is an error, in
every YAML file the pull request changed (comment lines are ignored). Outside a pull request
there is no range to check: the script prints a notice and succeeds.

Environment: BASE_REF (the pull request's base branch), CHECK_ALL=true to scan every tracked
YAML file instead of the changed ones.
"""
import os
import re
import subprocess
import sys

USES = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?pyrlyn/ci/\S*?@(?P<ref>[^\s'\"#]+)")
YAML = (".yml", ".yaml")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def files() -> list[str]:
    if os.environ.get("CHECK_ALL") == "true":
        names = git("ls-files").splitlines()
    else:
        base = os.environ.get("BASE_REF", "")
        if not base:
            print("::notice::no pull request base; nothing to check")
            return []
        names = git("diff", "--name-only", "--diff-filter=d", f"origin/{base}...HEAD").splitlines()
    return [n for n in names if n.endswith(YAML) and os.path.isfile(n)]


def main() -> int:
    bad = 0
    for name in files():
        with open(name, encoding="utf-8", errors="replace") as fh:
            for no, line in enumerate(fh, 1):
                m = USES.match(line)
                if m and m.group("ref") != "main":
                    print(f"::error file={name},line={no}::pyrlyn/ci is pinned to "
                          f"'{m.group('ref')}'; use '@main'")
                    print(f"{name}:{no}: {line.strip()}")
                    bad += 1
    if bad:
        print(f"{bad} pinned reference(s) to pyrlyn/ci; write `@main` (never a SHA or a tag)",
              file=sys.stderr)
        return 1
    print("no pinned pyrlyn/ci references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
