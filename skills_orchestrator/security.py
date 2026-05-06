"""Security helpers shared by CLI and runtime subprocess calls."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

DEFAULT_SAFE_PATH = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
CONSOLE_FALLBACKS = {
    "✓": "OK",
    "⚠": "!",
    "✗": "X",
    "○": "o",
    "→": "->",
    "←": "<-",
    "⏭": "SKIP",
    "❌": "X",
    "💡": "TIP:",
    "═": "=",
    "─": "-",
    "—": "-",
    "•": "-",
}


def safe_subprocess_env() -> dict[str, str]:
    """Return a narrow subprocess environment with an overrideable safe PATH."""
    env = {"PATH": os.environ.get("SKILLS_ORCHESTRATOR_SAFE_PATH", DEFAULT_SAFE_PATH)}
    if "HOME" in os.environ:
        env["HOME"] = os.environ["HOME"]
    return env


def subprocess_text_kwargs() -> dict[str, object]:
    """Return subprocess kwargs that decode text consistently on Windows too."""
    return {"text": True, "encoding": "utf-8", "errors": "replace"}


def _stream_uses_utf8() -> bool:
    encoding = getattr(sys.stdout, "encoding", None) or ""
    normalized = encoding.lower().replace("-", "")
    return "utf" in normalized or normalized == "cp65001"


def console_safe_symbol(symbol: str, fallback: str) -> str:
    """Return a symbol only when the active console can encode UTF-8 safely."""
    if _stream_uses_utf8():
        return symbol
    return fallback


def console_safe_text(text: str) -> str:
    """Replace common UI glyphs for non-UTF-8 consoles such as Windows GBK."""
    if _stream_uses_utf8():
        return text
    for symbol, fallback in CONSOLE_FALLBACKS.items():
        text = text.replace(symbol, fallback)
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    return text


def validate_path_within_root(path: Path, root: Path) -> Path:
    """Resolve and validate that path stays under root."""
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"路径逃逸安全限制: {resolved_path} 不在 {resolved_root} 内") from exc
    return resolved_path


def validate_identifier(value: str, field_name: str = "id") -> str:
    """Validate user-controlled identifiers before using them in file paths."""
    if not isinstance(value, str):
        raise ValueError(f"非法 {field_name}: 必须是字符串")
    if not SAFE_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"非法 {field_name}: {value!r}。仅允许字母、数字、下划线、连字符，长度 1-64。"
        )
    return value


def safe_child_path(root: Path, *parts: str) -> Path:
    """Join child path parts and ensure the final path remains inside root."""
    return validate_path_within_root(root.joinpath(*parts), root)


def parse_int_in_range(
    value: object, field_name: str, default: int, minimum: int, maximum: int
) -> int:
    """Parse an integer option and clamp it to a safe range."""
    if value is None:
        number = default
    elif isinstance(value, bool):
        raise ValueError(f"{field_name} 必须是整数")
    else:
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} 必须是整数") from exc

    return max(minimum, min(number, maximum))
