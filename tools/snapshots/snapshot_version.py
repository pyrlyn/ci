#!/usr/bin/env python3
"""Per-toolchain snapshot directories: version key, probe, status, migrate.

Snapshots that depend on the Xcode / macOS version live under
``<tests>/Snapshots/<key>/``. A run whose key has no directory skips its snapshot tests
(never fails, never records); a key joins the set only by an explicit record run plus a
commit of the new directory.

Key: ``xcode<short>-<build>-macos<major.minor.patch>``, e.g. ``xcode27.1-27A9275-macos27.0.1``.
``<PREFIX>_SNAPSHOT_VERSION`` (or ``SNAPSHOT_VERSION``) overrides it, e.g. ``hosted-pending``.
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


def parse_xcode(text: str) -> tuple[str, str]:
    """('27.1', '27A9275') from `xcodebuild -version` output."""
    version = re.search(r"^Xcode\s+(\S+)", text, re.M)
    build = re.search(r"^Build version\s+(\S+)", text, re.M)
    if not version or not build:
        raise ValueError(f"unrecognised xcodebuild -version output: {text!r}")
    return version.group(1), build.group(1)


def normalise_macos(version: str) -> str:
    """major.minor.patch: sw_vers prints '27.0' for patch 0, ProcessInfo prints '27.0.0'."""
    parts = (version.strip().split(".") + ["0", "0"])[:3]
    return ".".join(parts)


def compute_key(xcode_text: str | None, macos_version: str | None) -> str:
    if xcode_text and macos_version:
        version, build = parse_xcode(xcode_text)
        return f"xcode{version}-{build}-macos{normalise_macos(macos_version)}"
    return f"{platform.system().lower()}-{platform.machine().lower()}"


def run(cmd: list[str]) -> str | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def override(prefix: str) -> str | None:
    names = [f"{prefix}_SNAPSHOT_VERSION"] if prefix else []
    for name in [*names, "SNAPSHOT_VERSION"]:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def current_key(prefix: str) -> str:
    forced = override(prefix)
    if forced:
        return forced
    if platform.system() != "Darwin":
        return compute_key(None, None)
    return compute_key(run(["xcodebuild", "-version"]), run(["sw_vers", "-productVersion"]))


def cmd_key(args: argparse.Namespace) -> int:
    print(current_key(args.prefix))
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    """Prints the raw toolchain and writes it with the key to the job summary."""
    xcode = run(["xcodebuild", "-version"]) or "(no xcodebuild)"
    sw = run(["sw_vers"]) or "(no sw_vers)"
    native = compute_key(
        xcode if "Build version" in xcode else None, run(["sw_vers", "-productVersion"])
    )
    key = current_key(args.prefix)
    print(xcode, sw, sep="\n")
    print(f"native key: {native}\nactive key: {key}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write(
                f"### Snapshot toolchain\n\nnative key `{native}`, active key `{key}`\n\n"
                f"```\n{xcode.strip()}\n{sw.strip()}\n```\n"
            )
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as out:
            out.write(f"key={key}\nnative-key={native}\n")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """present=true/false per tests dir; exit 0 always (a missing dir means skip)."""
    key = current_key(args.prefix)
    present = (Path(args.tests) / "Snapshots" / key).is_dir()
    print(f"{args.tests}: key {key} -> {'compare' if present else 'skip'}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as out:
            out.write(f"present={str(present).lower()}\n")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    """Moves <tests>/__Snapshots__ to <tests>/Snapshots/<key> (use `git mv` semantics)."""
    tests = Path(args.tests)
    old = tests / "__Snapshots__"
    new = tests / "Snapshots" / args.to
    if not old.is_dir():
        print(f"nothing to migrate in {tests}", file=sys.stderr)
        return 1
    if new.exists():
        print(f"{new} already exists", file=sys.stderr)
        return 1
    new.parent.mkdir(parents=True, exist_ok=True)
    if args.git and subprocess.run(["git", "mv", str(old), str(new)]).returncode == 0:
        return 0
    shutil.move(str(old), str(new))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="", help="env prefix, e.g. COX -> COX_SNAPSHOT_VERSION")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("key").set_defaults(fn=cmd_key)
    sub.add_parser("probe").set_defaults(fn=cmd_probe)
    status = sub.add_parser("status")
    status.add_argument("tests")
    status.set_defaults(fn=cmd_status)
    migrate = sub.add_parser("migrate")
    migrate.add_argument("tests")
    migrate.add_argument("--to", required=True)
    migrate.add_argument("--git", action="store_true")
    migrate.set_defaults(fn=cmd_migrate)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
