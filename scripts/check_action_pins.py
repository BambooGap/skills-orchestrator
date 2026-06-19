#!/usr/bin/env python3
"""Fail when third-party GitHub Actions are not pinned to full commit SHAs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

USES_RE = re.compile(r"^\s*uses:\s*([^#\s]+)", re.MULTILINE)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    workflows_dir = root / ".github" / "workflows"
    workflows = sorted({*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml")})
    files = [root / "action.yml", *workflows]
    issues: list[str] = []
    for path in files:
        if not path.exists():
            continue
        rel = path.relative_to(root)
        for match in USES_RE.finditer(path.read_text(encoding="utf-8")):
            target = match.group(1).strip("'\"")
            if target.startswith(("./", "../", "docker://")):
                continue
            if "@" not in target:
                issues.append(f"{rel}: unpinned action {target!r}")
                continue
            ref = target.rsplit("@", 1)[1]
            if not SHA_RE.fullmatch(ref):
                issues.append(f"{rel}: action {target!r} is not pinned to a full commit SHA")
    if issues:
        print("GitHub Action pin check failed:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1
    print("All third-party GitHub Actions are pinned to full commit SHAs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
