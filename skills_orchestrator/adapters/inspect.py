"""Detect adjacent agent ecosystem surfaces in a repository."""

from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AdapterSurface:
    """Detected adapter surface with explicit authority boundaries."""

    id: str
    name: str
    direction: str
    authority: str
    detected: bool
    paths: list[str]
    verification: dict[str, Any]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_adapters(root: str | Path = ".") -> dict[str, Any]:
    """Inspect a repository for supported agent/skill integration surfaces."""
    root_path = Path(root).resolve()
    surfaces = [
        _agents_md_surface(root_path),
        _claude_skills_surface(root_path),
        _mcp_client_config_surface(root_path),
        _openai_agents_sdk_surface(root_path),
    ]
    return {
        "schema_version": "skills-orchestrator.adapters.v1",
        "root": str(root_path),
        "summary": {
            "surfaces": len(surfaces),
            "detected": sum(1 for surface in surfaces if surface.detected),
        },
        "surfaces": [surface.to_dict() for surface in surfaces],
    }


def discover_claude_skill_files(root: Path) -> list[Path]:
    """Return Claude-style skill bundle entrypoints under known roots."""
    candidates: list[Path] = []
    for skills_root in (root / ".claude" / "skills", root / ".agents" / "skills"):
        if not skills_root.is_dir():
            continue
        candidates.extend(sorted(path for path in skills_root.glob("*/SKILL.md") if path.is_file()))
    return candidates


def _agents_md_surface(root: Path) -> AdapterSurface:
    path = root / "AGENTS.md"
    detected = path.is_file()
    return AdapterSurface(
        id="agents-md",
        name="AGENTS.md",
        direction="export",
        authority="Generated project instruction bootstrap; canonical skill facts remain in skills.yaml and skill files.",
        detected=detected,
        paths=_relative_paths(root, [path] if detected else []),
        verification={
            "status": "verified" if detected else "not_detected",
            "checks": ["file exists"],
        },
        notes="Already supported by build and sync agents-md; adapter registry records the surface.",
    )


def _claude_skills_surface(root: Path) -> AdapterSurface:
    skill_files = discover_claude_skill_files(root)
    valid_files = [path for path in skill_files if _valid_claude_skill_entrypoint(path)]
    invalid_files = [path for path in skill_files if path not in set(valid_files)]
    return AdapterSurface(
        id="claude-skills",
        name="Claude Skills",
        direction="import-export",
        authority="External skill bundle layout; only */SKILL.md entrypoints are recognized as skills.",
        detected=bool(valid_files),
        paths=_relative_paths(root, valid_files),
        verification={
            "status": "verified" if valid_files else "not_detected",
            "checks": ["*/SKILL.md entrypoint", "frontmatter parse", "name or description"],
            "invalid_paths": _relative_paths(root, invalid_files),
        },
        notes="Reference files, examples, and scripts inside a skill directory are supporting assets, not separate skills.",
    )


def _mcp_client_config_surface(root: Path) -> AdapterSurface:
    candidates = [
        root / ".mcp.json",
        root / "mcp.json",
        root / ".cursor" / "mcp.json",
        root / ".claude" / "settings.json",
    ]
    existing = [path for path in candidates if path.is_file()]
    valid = [path for path in existing if _valid_mcp_client_config(path)]
    invalid = [path for path in existing if path not in set(valid)]
    return AdapterSurface(
        id="mcp-client-config",
        name="MCP client config",
        direction="export",
        authority="Client bootstrap for the existing skills-orchestrator stdio MCP server.",
        detected=bool(valid),
        paths=_relative_paths(root, valid),
        verification={
            "status": "verified" if valid else "not_detected",
            "checks": ["json parse", "mcpServers object"],
            "invalid_paths": _relative_paths(root, invalid),
        },
        notes="Use adapters export mcp-client-config to generate a minimal stdio client block.",
    )


def _openai_agents_sdk_surface(root: Path) -> AdapterSurface:
    paths = []
    if _pyproject_has_dependency(root / "pyproject.toml", "openai-agents"):
        paths.append(root / "pyproject.toml")
    if _requirements_has_dependency(root / "requirements.txt", "openai-agents"):
        paths.append(root / "requirements.txt")
    if _package_json_has_dependency(root / "package.json", "@openai/agents"):
        paths.append(root / "package.json")
    return AdapterSurface(
        id="openai-agents-sdk",
        name="OpenAI Agents SDK",
        direction="export",
        authority="Generated scaffold showing how to attach the existing MCP server to an Agent.",
        detected=bool(paths),
        paths=_relative_paths(root, paths),
        verification={
            "status": "dependency_detected" if paths else "not_detected",
            "checks": ["dependency declaration scan"],
            "recommended_checks": ["generated code py_compile", "optional SDK construction test"],
        },
        notes="No project-level auto-discovery format is assumed.",
    )


def _pyproject_has_dependency(path: Path, dependency_name: str) -> bool:
    if not path.is_file():
        return False
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return False
    project = data.get("project", {})
    deps = list(project.get("dependencies", []))
    optional = project.get("optional-dependencies", {})
    for values in optional.values():
        if isinstance(values, list):
            deps.extend(values)
    return any(_dependency_matches(dep, dependency_name) for dep in deps)


def _requirements_has_dependency(path: Path, dependency_name: str) -> bool:
    if not path.is_file():
        return False
    return any(
        _dependency_matches(line.strip(), dependency_name) for line in path.read_text().splitlines()
    )


def _package_json_has_dependency(path: Path, dependency_name: str) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        deps = data.get(section, {})
        if isinstance(deps, dict) and dependency_name in deps:
            return True
    return False


def _dependency_matches(requirement: str, dependency_name: str) -> bool:
    if not requirement or requirement.startswith("#"):
        return False
    normalized = requirement.split(";", 1)[0].split("[", 1)[0].strip().lower()
    for separator in ("==", ">=", "<=", "~=", "!=", ">", "<", "="):
        normalized = normalized.split(separator, 1)[0].strip()
    return normalized == dependency_name.lower()


def _relative_paths(root: Path, paths: list[Path]) -> list[str]:
    result = []
    for path in paths:
        try:
            result.append(str(path.resolve().relative_to(root)))
        except ValueError:
            result.append(path.name)
    return sorted(result)


def read_claude_skill_frontmatter(path: Path) -> dict[str, Any]:
    """Read frontmatter from a Claude SKILL.md entrypoint."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    try:
        data = yaml.safe_load(content[3:end]) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _valid_claude_skill_entrypoint(path: Path) -> bool:
    frontmatter = read_claude_skill_frontmatter(path)
    return bool(frontmatter.get("name") or frontmatter.get("description"))


def _valid_mcp_client_config(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    return isinstance(servers, dict)
