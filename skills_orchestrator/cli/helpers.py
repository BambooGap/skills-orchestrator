"""Shared CLI helpers — styling, context parsing, pipeline loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
import yaml

from skills_orchestrator.security import (
    console_safe_symbol,
    console_safe_text,
    safe_child_path,
    validate_identifier,
)


def _ok(msg: str) -> str:
    return click.style(console_safe_symbol("✓", "OK"), fg="green") + f" {console_safe_text(msg)}"


def _warn(msg: str) -> str:
    return click.style(console_safe_symbol("⚠", "!"), fg="yellow") + f" {console_safe_text(msg)}"


def _err(msg: str) -> str:
    return click.style(console_safe_symbol("✗", "X"), fg="red") + f" {console_safe_text(msg)}"


def _parse_context(context_str: str) -> dict:
    """解析 context 参数：支持 JSON 字符串或 @文件路径。"""
    if context_str.strip().startswith("@"):
        filepath = Path(context_str.strip()[1:]).resolve()
        cwd = Path.cwd().resolve()
        try:
            filepath.relative_to(cwd)
        except ValueError:
            raise click.BadParameter(f"安全限制：context 文件必须在当前目录内: {filepath}")
        if not filepath.exists():
            raise click.BadParameter(f"context 文件不存在: {filepath}")
        return json.loads(filepath.read_text(encoding="utf-8"))
    return json.loads(context_str)


def _resolve_pipelines_dir(config_path: Optional[str] = None) -> Path:
    """统一解析 pipelines 目录，优先级：
    1. 各 pipeline 命令的 --pipelines-dir 参数（已实现）
    2. config 文件同级目录的 pipelines/
    3. 当前目录 config/pipelines
    4. 包内 config/pipelines（开发环境 fallback）
    """
    if config_path:
        config_dir = Path(config_path).parent
        pipelines_dir = config_dir / "pipelines"
        if pipelines_dir.is_dir():
            return pipelines_dir

    pipelines_dir = Path("config/pipelines")
    if pipelines_dir.is_dir():
        return pipelines_dir

    package_pipelines = Path(__file__).parent.parent.parent / "config" / "pipelines"
    if package_pipelines.is_dir():
        return package_pipelines

    return pipelines_dir


def _load_pipeline(pipeline_id: str, config_path: Optional[str] = None):
    """加载 Pipeline 定义，返回 Pipeline 对象或 None"""
    from skills_orchestrator.pipeline.loader import PipelineLoader

    pipelines_dir = _resolve_pipelines_dir(config_path)
    pipeline_id = validate_identifier(pipeline_id, "pipeline_id")
    yaml_path = safe_child_path(pipelines_dir, f"{pipeline_id}.yaml")
    if not yaml_path.exists():
        return None
    loader = PipelineLoader()
    try:
        return loader.load(str(yaml_path))
    except yaml.YAMLError as e:
        click.echo(f"Pipeline YAML 解析失败: {e}", err=True)
        return None
    except Exception as e:
        click.echo(f"加载 Pipeline 失败: {e}", err=True)
        return None


def _slugify(text: str) -> str:
    """将文本转换为 slug 格式，保留中文、字母、数字、连字符"""
    import hashlib
    import re

    result = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower()).strip("-")
    if not result or result.strip("-") == "":
        return f"skill-{hashlib.sha1(text.encode()).hexdigest()[:8]}"
    return result


def _parse_frontmatter(content: str) -> dict:
    """解析 YAML frontmatter（--- ... ---），返回 meta dict；无 frontmatter 时推断基本信息。"""
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            fm_text = content[3:end].strip()
            try:
                meta = yaml.safe_load(fm_text) or {}
                if isinstance(meta, dict):
                    if "summary" not in meta and "description" in meta:
                        meta["summary"] = meta["description"]
                    if "tags" in meta and isinstance(meta["tags"], str):
                        meta["tags"] = [t.strip() for t in meta["tags"].split(",") if t.strip()]
                    return meta
            except yaml.YAMLError:
                pass

    meta = {}
    lines = content.splitlines()
    for line in lines:
        if line.startswith("# "):
            meta["name"] = line[2:].strip()
            break
    in_para = False
    para_lines = []
    for line in lines[1:]:
        if line.startswith("#"):
            if in_para:
                break
            continue
        if line.strip() == "":
            if in_para:
                break
        else:
            in_para = True
            para_lines.append(line.strip())
    if para_lines:
        summary = " ".join(para_lines)
        meta["summary"] = summary[:120] + ("..." if len(summary) > 120 else "")
    return meta


def _append_skills_to_yaml(config_path: str, new_entries: list[dict]) -> None:
    """把新 skill 条目追加到现有 skills.yaml，如不存在则创建最小配置。"""
    path = Path(config_path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {
            "version": "1.0",
            "zones": [
                {
                    "id": "default",
                    "name": "默认区",
                    "load_policy": "free",
                    "priority": 0,
                    "rules": [],
                }
            ],
            "skills": [],
            "combos": [],
        }

    existing_ids = {s["id"] for s in raw.get("skills", [])}
    added = 0
    for entry in new_entries:
        if entry["id"] not in existing_ids:
            raw.setdefault("skills", []).append(entry)
            added += 1

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    click.echo(
        _ok(f"追加 {added} 个 skill 到 {config_path}（跳过 {len(new_entries) - added} 个已存在）")
    )
