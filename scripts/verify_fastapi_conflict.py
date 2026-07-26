#!/usr/bin/env python3
"""Classify the known FastAPI/Starlette incompatibility without masking other failures."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


NETWORK_FAILURE_MARKERS = re.compile(
    (
        r"newconnectionerror|nameresolutionerror|readtimeout|connectionerror|"
        r"could not fetch url|could not reach|temporary failure in name resolution|"
        r"failed to establish a new connection|connection reset|connection timed out|"
        r"network is unreachable"
    ),
    re.IGNORECASE,
)
INSTALL_RESOLVER_MARKERS = re.compile(
    r"resolutionimpossible|conflicting dependencies|dependency conflict|"
    r"error:\s+cannot install[\s\S]+because",
    re.IGNORECASE,
)
PIP_CHECK_CONFLICT_LINE = re.compile(
    (
        r"^fastapi\s+\S+\s+has requirement\s+"
        r"starlette(?P<specifier>[<>=!~]\S*),\s+but you have\s+"
        r"starlette\s+\S+\.?$"
    ),
    re.IGNORECASE,
)


def _mentions_fastapi_and_starlette(text: str) -> bool:
    lowered = text.lower()
    return "fastapi" in lowered and "starlette" in lowered


def has_network_failure(text: str) -> bool:
    return NETWORK_FAILURE_MARKERS.search(text) is not None


def is_install_resolver_conflict(text: str) -> bool:
    return (
        _mentions_fastapi_and_starlette(text)
        and not has_network_failure(text)
        and INSTALL_RESOLVER_MARKERS.search(text) is not None
    )


def is_fastapi_starlette_conflict(text: str) -> bool:
    """Accept exactly one unsatisfied FastAPI-to-Starlette ``pip check`` line."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        return False

    match = PIP_CHECK_CONFLICT_LINE.fullmatch(lines[0])
    if match is None:
        return False

    return bool(match.group("specifier"))


def verify_rejection(
    *,
    install_status: int,
    install_log: str,
    pip_check_status: int | None = None,
    pip_check_log: str = "",
) -> tuple[bool, str]:
    if install_status != 0:
        if has_network_failure(install_log):
            return False, "installation failed because of a network or package-index error"
        if is_install_resolver_conflict(install_log):
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
