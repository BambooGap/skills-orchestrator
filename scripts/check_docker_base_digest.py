#!/usr/bin/env python3
"""Fail when Dockerfile base images are not pinned to sha256 digests."""

from __future__ import annotations

import re
import sys
from pathlib import Path

FROM_RE = re.compile(r"^\s*FROM\s+(?P<image>\S+)", re.IGNORECASE)
SHA_REF_RE = re.compile(r"@sha256:[0-9a-f]{64}(?:\s|$)")

EXEMPT_BASES = {"scratch"}


def find_unpinned_base_images(path: Path, *, display_path: Path | None = None) -> list[str]:
    label = display_path or path
    issues: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = FROM_RE.match(line)
        if not match:
            continue
        image = match.group("image")
        if image in EXEMPT_BASES:
            continue
        if SHA_REF_RE.search(line):
            continue
        issues.append(f"{label}:{line_number}: Docker base image is not digest-pinned: {image}")
    return issues


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    dockerfile = root / "Dockerfile"
    issues = find_unpinned_base_images(dockerfile, display_path=dockerfile.relative_to(root))
    if issues:
        print("Docker base image digest check failed:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1
    print("All Docker base images are pinned to sha256 digests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
