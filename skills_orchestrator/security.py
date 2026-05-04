"""Security helpers shared by CLI and runtime subprocess calls."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SAFE_PATH = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"


def safe_subprocess_env() -> dict[str, str]:
    """Return a narrow subprocess environment with an overrideable safe PATH."""
    env = {"PATH": os.environ.get("SKILLS_ORCHESTRATOR_SAFE_PATH", DEFAULT_SAFE_PATH)}
    if "HOME" in os.environ:
        env["HOME"] = os.environ["HOME"]
    return env


def validate_path_within_root(path: Path, root: Path) -> Path:
    """Resolve and validate that path stays under root."""
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"路径逃逸安全限制: {resolved_path} 不在 {resolved_root} 内") from exc
    return resolved_path
