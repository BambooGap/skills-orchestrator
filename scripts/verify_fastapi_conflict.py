#!/usr/bin/env python3
"""Classify the known FastAPI/Starlette incompatibility without masking other failures."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


CONFLICT_MARKERS = re.compile(
    r"conflict|incompatib|resolutionimpossible|depends on|requires?|has requirement",
    re.IGNORECASE,
)


def is_fastapi_starlette_conflict(text: str) -> bool:
    lowered = text.lower()
    return (
        "fastapi" in lowered
        and "starlette" in lowered
        and CONFLICT_MARKERS.search(text) is not None
    )


def verify_rejection(
    *,
    install_status: int,
    install_log: str,
    pip_check_status: int | None = None,
    pip_check_log: str = "",
) -> tuple[bool, str]:
    if install_status != 0:
        if is_fastapi_starlette_conflict(install_log):
            return True, "known FastAPI/Starlette conflict rejected during installation"
        return False, "installation failed for a reason other than the known dependency conflict"

    if pip_check_status is None:
        return False, "installation succeeded but pip check was not executed"
    if pip_check_status == 0:
        return False, "known-incompatible shared environment passed pip check"
    if not is_fastapi_starlette_conflict(pip_check_log):
        return False, "pip check failed without the expected FastAPI/Starlette conflict"
    return True, "known FastAPI/Starlette conflict detected by pip check"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-status", type=int, required=True)
    parser.add_argument("--install-log", type=Path, required=True)
    parser.add_argument("--pip-check-status", type=int)
    parser.add_argument("--pip-check-log", type=Path)
    args = parser.parse_args(argv)

    install_log = args.install_log.read_text(encoding="utf-8", errors="replace")
    pip_check_log = (
        args.pip_check_log.read_text(encoding="utf-8", errors="replace")
        if args.pip_check_log
        else ""
    )
    ok, message = verify_rejection(
        install_status=args.install_status,
        install_log=install_log,
        pip_check_status=args.pip_check_status,
        pip_check_log=pip_check_log,
    )
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
