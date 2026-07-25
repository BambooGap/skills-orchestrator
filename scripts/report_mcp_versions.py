#!/usr/bin/env python3
"""Print the resolved MCP runtime package versions as stable JSON."""

from __future__ import annotations

import json
from importlib import metadata


PACKAGES = ("mcp", "starlette", "sse-starlette", "fastapi")


def collect_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in PACKAGES:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            continue
    return versions


def main() -> int:
    print(json.dumps(collect_versions(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
