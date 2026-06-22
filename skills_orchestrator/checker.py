"""Structured skill checks for CLI and CI integrations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from skills_orchestrator.compiler import Parser, Resolver, SkillsLock
from skills_orchestrator.compiler.parser import SkillDiagnosticError
from skills_orchestrator.diagnostic import Diagnostic, DiagnosticReport, PolicyTraceItem
from skills_orchestrator.models import Config, ResolvedConfig, SkillMeta, Zone
from skills_orchestrator.policy.packs import (
    ENGINEERING_GRADE_PACK,
    TEAM_STANDARD_PACK,
    normalize_policy_packs,
    policy_pack_diagnostics,
)
from skills_orchestrator.security import validate_skill_id


DEFAULT_MAX_SKILL_BYTES = 20_000


@dataclass(frozen=True)
class SkillOccurrence:
    skill_id: str
    path: Path
    line: int


def run_check(
    config_path: str,
    *,
    zone_id: str | None = None,
    check_lock: str | None = None,
    max_skill_bytes: int = DEFAULT_MAX_SKILL_BYTES,
    policy_packs: list[str] | tuple[str, ...] | None = None,
) -> DiagnosticReport:
    """Run non-mutating checks and return structured diagnostics."""
    parser = Parser(config_path)
    try:
        cfg = parser.parse()
    except SkillDiagnosticError as exc:
        diagnostic = Diagnostic.from_rule(
            exc.rule_id,
            str(exc),
            file=exc.file,
            line=exc.line,
            skill_id=exc.skill_id,
            suggested_fix=exc.suggested_fix,
        )
        return DiagnosticReport(
            diagnostics=[diagnostic],
            total_skills=0,
            zones=0,
            combos=0,
            policy_trace=[_trace_from_diagnostic(diagnostic, scope="parser")],
        )

    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_duplicate_id_diagnostics(config_path))
    diagnostics.extend(_metadata_diagnostics(cfg, max_skill_bytes=max_skill_bytes))
    diagnostics.extend(_asymmetric_conflict_diagnostics(cfg))
    diagnostics.extend(policy_pack_diagnostics(cfg, policy_packs or []))

    target_zone = _select_zone(cfg, zone_id)
    resolved: ResolvedConfig | None = None
    try:
        resolved = Resolver(cfg).resolve(target_zone)
    except ValueError as exc:
        if "冲突" not in str(exc):
            raise
        diagnostics.append(
            Diagnostic.from_rule(
                "SO003",
                str(exc),
                file=_relative_path(Path(config_path).resolve(), Path.cwd().resolve()),
                line=1,
                suggested_fix="Adjust load_policy or priority, or remove an incorrect conflict_with declaration.",
            )
        )

    if check_lock and resolved is not None:
        diagnostics.extend(_lock_diagnostics(resolved, check_lock))

    return DiagnosticReport(
        diagnostics=diagnostics,
        total_skills=len(cfg.skills),
        zones=len(cfg.zones),
        combos=len(cfg.combos),
        policy_trace=_policy_trace(
            cfg,
            diagnostics,
            policy_packs=policy_packs or [],
            zone_id=zone_id,
            check_lock=check_lock,
            max_skill_bytes=max_skill_bytes,
            resolver_ran=resolved is not None,
        ),
    )


def fatal_error_report(message: str, *, config_path: str | None = None) -> DiagnosticReport:
    """Create a machine-readable report for fatal parse/config errors."""
    diagnostics = [
        Diagnostic.from_rule(
            "SO000",
            message,
            file=_relative_path(Path(config_path).resolve(), Path.cwd().resolve())
            if config_path
            else None,
            line=1 if config_path else None,
            suggested_fix="Fix the configuration or input path, then run the check again.",
        )
    ]
    return DiagnosticReport(
        diagnostics=diagnostics,
        total_skills=0,
        zones=0,
        combos=0,
        policy_trace=[_trace_from_diagnostic(diagnostics[0], scope="fatal")],
    )


def _policy_trace(
    cfg: Config,
    diagnostics: list[Diagnostic],
    *,
    policy_packs: list[str] | tuple[str, ...],
    zone_id: str | None,
    check_lock: str | None,
    max_skill_bytes: int,
    resolver_ran: bool,
) -> list[PolicyTraceItem]:
    traces = [_trace_from_diagnostic(diagnostic) for diagnostic in diagnostics]
    failed_rules = {diagnostic.rule_id for diagnostic in diagnostics}
    normalized_packs = normalize_policy_packs(policy_packs)
    facts = {
        "skills": len(cfg.skills),
        "zones": len(cfg.zones),
        "combos": len(cfg.combos),
        "zone": zone_id or "",
    }

    base_rules = [
        ("SO001", "metadata", "All skills include summary or description metadata."),
        ("SO002", "structure", "No duplicate skill ids were detected."),
        (
            "SO004",
            "conflict",
            "Conflict declarations are symmetric or intentionally one-way without findings.",
        ),
        (
            "SO005",
            "metadata",
            f"No skill exceeded the {max_skill_bytes} byte review threshold.",
        ),
    ]
    for rule_id, scope, reason in base_rules:
        if rule_id not in failed_rules:
            traces.append(_pass_trace(rule_id, scope, reason, facts))

    if resolver_ran and "SO003" not in failed_rules:
        traces.append(
            _pass_trace(
                "SO003", "resolver", "Resolver completed without unresolved conflicts.", facts
            )
        )

    if check_lock and "SO007" not in failed_rules:
        traces.append(_pass_trace("SO007", "lock", "Lock file matches resolved skills.", facts))

    if TEAM_STANDARD_PACK in normalized_packs or ENGINEERING_GRADE_PACK in normalized_packs:
        for rule_id, reason in (
            ("SO008", "All skills include owner metadata."),
            ("SO009", "All skills include source metadata."),
            ("SO010", "All skills include version metadata."),
            ("SO011", "All skill lifecycle values are allowed."),
            ("SO012", "Required skills include approver metadata."),
        ):
            if rule_id not in failed_rules:
                traces.append(
                    _pass_trace(
                        rule_id,
                        "policy_pack",
                        reason,
                        facts,
                        policy_pack=TEAM_STANDARD_PACK,
                    )
                )

    if ENGINEERING_GRADE_PACK in normalized_packs:
        for rule_id, reason in (
            ("SO014", "All skills include review-window metadata."),
            ("SO015", "All review-window dates are valid."),
            ("SO016", "No skill review window has expired."),
            ("SO018", "All skills include license metadata."),
            ("SO019", "All skill licenses are allowed."),
            ("SO020", "Externally sourced skills include import provenance metadata."),
        ):
            if rule_id not in failed_rules:
                traces.append(
                    _pass_trace(
                        rule_id,
                        "policy_pack",
                        reason,
                        facts,
                        policy_pack=ENGINEERING_GRADE_PACK,
                    )
                )

    return traces


def _trace_from_diagnostic(diagnostic: Diagnostic, *, scope: str | None = None) -> PolicyTraceItem:
    return PolicyTraceItem(
        rule_id=diagnostic.rule_id,
        outcome="fail",
        scope=scope or (diagnostic.category.value if diagnostic.category else "diagnostic"),
        reason=diagnostic.message,
        input_facts=diagnostic.metadata,
        file=diagnostic.file,
        line=diagnostic.line,
        skill_id=diagnostic.skill_id,
        policy_pack=diagnostic.metadata.get("policy_pack"),
        diagnostic=diagnostic.to_dict(),
    )


def _pass_trace(
    rule_id: str,
    scope: str,
    reason: str,
    input_facts: dict[str, object],
    *,
    policy_pack: str | None = None,
) -> PolicyTraceItem:
    return PolicyTraceItem(
        rule_id=rule_id,
        outcome="pass",
        scope=scope,
        reason=reason,
        input_facts=dict(input_facts),
        policy_pack=policy_pack,
    )


def _select_zone(cfg: Config, zone_id: str | None) -> Zone | None:
    if not zone_id:
        return None
    zone = next((z for z in cfg.zones if z.id == zone_id), None)
    if zone is None:
        raise ValueError(f"Zone '{zone_id}' 不存在")
    return zone


def _metadata_diagnostics(cfg: Config, *, max_skill_bytes: int) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for skill in cfg.skills:
        path = _skill_path(cfg, skill)
        rel = _relative_path(path, Path(cfg.base_dir))

        if not skill.summary.strip():
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO001",
                    f"Skill '{skill.id}' is missing summary/description metadata.",
                    file=rel,
                    line=_frontmatter_line(path, ("summary", "description")),
                    skill_id=skill.id,
                    suggested_fix="Add a concise summary or official description field.",
                )
            )

        size = path.stat().st_size if path.exists() else 0
        if size > max_skill_bytes:
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO005",
                    f"Skill '{skill.id}' is {size} bytes, above the {max_skill_bytes} byte review threshold.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Split long reference material into progressive disclosure files or scripts.",
                    metadata={"bytes": size, "threshold": max_skill_bytes},
                )
            )

    return diagnostics


def _asymmetric_conflict_diagnostics(cfg: Config) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    skill_map = {s.id: s for s in cfg.skills}
    for skill in cfg.skills:
        for conflict_id in skill.conflict_with:
            other = skill_map.get(conflict_id)
            if other is None or skill.id in other.conflict_with:
                continue
            path = _skill_path(cfg, skill)
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO004",
                    f"Skill '{skill.id}' declares conflict_with '{conflict_id}', but '{conflict_id}' does not declare '{skill.id}'.",
                    file=_relative_path(path, Path(cfg.base_dir)),
                    line=_frontmatter_line(path, ("conflict_with",)),
                    skill_id=skill.id,
                    suggested_fix=f"Add '{skill.id}' to '{conflict_id}' conflict_with if the conflict is truly mutual.",
                    metadata={"conflicting_skill": conflict_id},
                )
            )
    return diagnostics


def _lock_diagnostics(resolved: ResolvedConfig, lock_path: str) -> list[Diagnostic]:
    path = Path(lock_path)
    if not path.exists():
        raise FileNotFoundError(f"Lock 文件不存在: {path}")

    diagnostics = []
    for issue in SkillsLock.check(resolved, str(path)):
        diagnostics.append(
            Diagnostic.from_rule(
                "SO007",
                issue,
                file=_relative_path(path.resolve(), Path.cwd().resolve()),
                line=1,
                suggested_fix="Regenerate skills.lock.json after reviewing the behavior change.",
                metadata={"issue": issue},
            )
        )
    return diagnostics


def _duplicate_id_diagnostics(config_path: str) -> list[Diagnostic]:
    occurrences = _skill_id_occurrences(config_path)
    diagnostics: list[Diagnostic] = []
    for skill_id, items in occurrences.items():
        if len(items) <= 1:
            continue
        first = items[0]
        first_path = _relative_path(first.path, Path.cwd().resolve())
        for duplicate in items[1:]:
            duplicate_path = _relative_path(duplicate.path, Path.cwd().resolve())
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO002",
                    f"Duplicate skill id '{skill_id}' also appears in {first_path}. Parser keeps the first occurrence.",
                    file=duplicate_path,
                    line=duplicate.line,
                    skill_id=skill_id,
                    suggested_fix="Rename one skill id or remove the duplicate file.",
                    metadata={
                        "first_path": first_path,
                        "duplicate_path": duplicate_path,
                    },
                )
            )
    return diagnostics


def _skill_id_occurrences(config_path: str) -> dict[str, list[SkillOccurrence]]:
    config_file = Path(config_path)
    parser = Parser(config_path)
    raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    occurrences: dict[str, list[SkillOccurrence]] = {}

    for raw_skill in raw.get("skills", []):
        skill_id = raw_skill.get("id")
        if not skill_id:
            continue
        _add_occurrence(
            occurrences,
            skill_id,
            config_file.resolve(),
            _yaml_key_line(config_file, f"id: {skill_id}"),
        )

    for dir_expr in raw.get("skill_dirs", []):
        dir_path = (parser.config_dir / parser._expand_skill_dir(dir_expr)).resolve()
        if not dir_path.exists():
            continue
        for md_file in sorted(dir_path.rglob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            meta = Parser._read_frontmatter(content)
            raw_id = meta.get("id", md_file.stem)
            try:
                skill_id = validate_skill_id(raw_id, "skill id")
            except ValueError:
                skill_id = str(raw_id)
            _add_occurrence(
                occurrences,
                skill_id,
                md_file.resolve(),
                _frontmatter_line(md_file, ("id",)),
            )

    return occurrences


def _add_occurrence(
    occurrences: dict[str, list[SkillOccurrence]], skill_id: str, path: Path, line: int
) -> None:
    occurrences.setdefault(skill_id, []).append(SkillOccurrence(skill_id, path, line))


def _skill_path(cfg: Config, skill: SkillMeta) -> Path:
    p = Path(skill.path)
    if p.is_absolute():
        return p
    return (Path(cfg.base_dir) / p).resolve()


def _frontmatter_line(path: Path, keys: Iterable[str]) -> int:
    if not path.exists():
        return 1
    key_prefixes = tuple(f"{key}:" for key in keys)
    in_frontmatter = False
    try:
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if index == 1 and stripped == "---":
                in_frontmatter = True
                continue
            if in_frontmatter and stripped == "---":
                return 1
            if in_frontmatter and stripped.startswith(key_prefixes):
                return index
    except UnicodeDecodeError:
        return 1
    return 1


def _yaml_key_line(path: Path, needle: str) -> int:
    try:
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if needle in line:
                return index
    except UnicodeDecodeError:
        return 1
    return 1


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return path.name
