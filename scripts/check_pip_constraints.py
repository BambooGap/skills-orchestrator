#!/usr/bin/env python3
"""Fail when automation installs Python dependencies without constraints.txt."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PIP_INSTALL_RE = re.compile(r"\b(?:python(?:\d(?:\.\d+)*)?\s+-m\s+)?pip\s+install\b")

ALLOWED_UNCONSTRAINED_SNIPPETS = (
    "dist/*.whl",
    "--upgrade pip",
)


def iter_logical_lines(text: str) -> list[tuple[int, str]]:
    """Return shell-ish logical lines, joining backslash continuations."""
    logical: list[tuple[int, str]] = []
    start_line = 1
    buffer: list[str] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.rstrip()
        if not buffer:
            start_line = line_number
        if stripped.endswith("\\"):
            buffer.append(stripped[:-1])
            continue
        buffer.append(stripped)
        logical.append((start_line, " ".join(part.strip() for part in buffer)))
        buffer = []

    if buffer:
        logical.append((start_line, " ".join(part.strip() for part in buffer)))
    return logical


def find_unconstrained_installs(path: Path, *, display_path: Path | None = None) -> list[str]:
    issues: list[str] = []
    label = display_path or path
    text = path.read_text(encoding="utf-8")
    for line_number, command in iter_logical_lines(text):
        stripped = command.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not PIP_INSTALL_RE.search(stripped):
            continue
        if "constraints.txt" in stripped or "PIP_CONSTRAINT" in stripped:
            continue
        if any(snippet in stripped for snippet in ALLOWED_UNCONSTRAINED_SNIPPETS):
            continue
        issues.append(f"{label}:{line_number}: pip install is missing constraints.txt: {stripped}")
    return issues


def automation_files(root: Path) -> list[Path]:
    files = [root / "action.yml", root / "Dockerfile"]
    workflows = sorted((root / ".github" / "workflows").glob("*.yml"))
    workflows.extend(sorted((root / ".github" / "workflows").glob("*.yaml")))
    return [path for path in [*files, *workflows] if path.exists()]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    issues: list[str] = []
    for path in automation_files(root):
        issues.extend(find_unconstrained_installs(path, display_path=path.relative_to(root)))

    if issues:
        print("pip install constraints check failed:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1
    print("All automation pip install commands are constrained or explicitly exempt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
