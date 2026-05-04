"""import command — 从 GitHub 导入 skill 文件并注册到 skills.yaml"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import click

from skills_orchestrator.security import safe_subprocess_env

from .helpers import (
    _append_skills_to_yaml,
    _err,
    _parse_frontmatter,
    _slugify,
    _warn,
)


# ─── GitHub import helpers ────────────────────────────────────────


def _gh_api(api_path: str) -> object:
    """优先用 gh CLI（已认证，无限速），失败则回退到 urllib。"""
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "api", api_path],
            capture_output=True,
            text=True,
            timeout=15,
            env=safe_subprocess_env(),
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 回退：未认证的 GitHub API
    url = f"https://api.github.com/{api_path.lstrip('/')}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "skills-orchestrator/1.0",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _validate_github_url(url: str) -> bool:
    """验证 URL 是否为合法的 GitHub 域名，防止 SSRF 攻击"""
    try:
        parsed = urlparse(url)
        return parsed.hostname in (
            "github.com",
            "raw.githubusercontent.com",
            "api.github.com",
        )
    except Exception:
        return False


def _fetch_raw(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "skills-orchestrator/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def _github_url_to_parts(source: str) -> tuple[str, str, str, str]:
    """解析 GitHub URL，返回 (owner, repo, ref, path)。"""
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)(?:/(tree|blob)/([^/]+)(/.*)?)?",
        source.rstrip("/"),
    )
    if not m:
        raise ValueError(f"无法解析 GitHub URL: {source}")
    owner, repo = m.group(1), m.group(2)
    ref = m.group(4) or "main"
    path = (m.group(5) or "").lstrip("/")
    return owner, repo, ref, path


def _fetch_github_skills(source: str) -> list[tuple[str, str]]:
    """返回 [(filename, content), ...]。

    支持两种仓库结构：
    1. 扁平：目录下直接放 *.md
    2. 子目录：每个 skill 一个子目录，内含 SKILL.md（如 karpathy-skills 格式）
    """
    owner, repo, ref, path = _github_url_to_parts(source)

    # 单文件（blob URL）
    if "/blob/" in source:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
        filename = Path(path).name
        return [(filename, _fetch_raw(raw_url))]

    # 目录或仓库根
    api_path = f"repos/{owner}/{repo}/contents/{path}"
    if ref != "main":
        api_path += f"?ref={ref}"

    try:
        items = _gh_api(api_path)
    except Exception as e:
        raise RuntimeError(f"GitHub API 请求失败: {e}\n提示：安装 gh CLI 并登录可绕过限速") from e

    if not isinstance(items, list):
        raise RuntimeError(f"API 返回格式异常（期望列表，实际: {type(items).__name__}）")

    results = []
    for item in items:
        # 扁平结构：直接是 .md 文件
        if (
            item.get("type") == "file"
            and item["name"].endswith(".md")
            and not item["name"].lower().startswith("readme")
            and item["name"] not in ("CLAUDE.md", "CURSOR.md", "EXAMPLES.md")
        ):
            try:
                content = _fetch_raw(item["download_url"])
                results.append((item["name"], content))
                click.echo(f"  ✓ {item['name']}")
            except Exception as e:
                click.echo(_warn(f"跳过 {item['name']}: {e}"))

        # 子目录结构：进入子目录找 SKILL.md（karpathy-skills 格式）
        elif item.get("type") == "dir" and not item["name"].startswith("."):
            sub_api_path = f"repos/{owner}/{repo}/contents/{item['path']}"
            if ref != "main":
                sub_api_path += f"?ref={ref}"
            try:
                sub_items = _gh_api(sub_api_path)
                if isinstance(sub_items, list):
                    for sub in sub_items:
                        if sub.get("type") == "file" and sub["name"].upper() == "SKILL.MD":
                            content = _fetch_raw(sub["download_url"])
                            filename = f"{item['name']}.md"
                            results.append((filename, content))
                            click.echo(f"  ✓ {item['name']}/SKILL.md → {filename}")
            except Exception as e:
                click.echo(_warn(f"跳过子目录 {item['name']}: {e}"))

    return results


# ─── CLI command ──────────────────────────────────────────────────


@click.command("import")
@click.argument("source")
@click.option("--skills-dir", "-d", default="./skills", help="本地 skills 存放目录")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径（追加导入记录）")
@click.option("--dry-run", is_flag=True, help="预览导入结果，不实际写入文件")
@click.option("--force", is_flag=True, help="强制覆盖已存在的文件")
def import_skill(source: str, skills_dir: str, config: str, dry_run: bool, force: bool):
    """从 GitHub 导入 skill 文件并注册到 skills.yaml

    \b
    示例：
      skills-orchestrator import https://github.com/user/repo
      skills-orchestrator import https://github.com/user/repo/tree/main/skills
      skills-orchestrator import https://github.com/user/repo/blob/main/my-skill.md
    """
    skills_path = Path(skills_dir)
    if not dry_run:
        skills_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"来源: {source}\n")

    try:
        if not _validate_github_url(source):
            raise ValueError(
                "安全限制：只支持 GitHub URL (github.com, raw.githubusercontent.com)\n"
                "支持的来源：GitHub repo / 目录 / 单文件，或 raw.githubusercontent.com 直链"
            )

        parsed_host = urlparse(source).hostname or ""
        if parsed_host == "raw.githubusercontent.com":
            if not source.endswith(".md"):
                raise ValueError("raw.githubusercontent.com 链接必须以 .md 结尾")
            filename = source.rsplit("/", 1)[-1]
            content = _fetch_raw(source)
            files = [(filename, content)]
        else:
            files = _fetch_github_skills(source)
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)

    if not files:
        click.echo(_warn("未找到任何 .md 文件"))
        if "github.com" in source and "/tree/" not in source and "/blob/" not in source:
            click.echo("  提示：尝试指定子目录，例如：")
            click.echo(f"    skills-orchestrator import {source.rstrip('/')}/tree/main/skills")
        return

    click.echo(f"\n共 {len(files)} 个文件：")

    new_entries = []
    for filename, content in files:
        meta = _parse_frontmatter(content)
        stem = Path(filename).stem
        skill_id = meta.get("id", _slugify(stem))
        entry = {
            "id": skill_id,
            "name": meta.get("name", stem.replace("-", " ").title()),
            "path": f"${{SKILLS_ROOT}}/{filename}",
            "summary": meta.get("summary", f"从 {source} 导入"),
            "tags": meta.get("tags", []),
            "load_policy": meta.get("load_policy", "free"),
            "priority": int(meta.get("priority", 50)),
            "zones": ["default"],
            "conflict_with": [],
        }

        if dry_run:
            click.echo(f"  {click.style('[dry-run]', fg='yellow')} {filename}")
            click.echo(f"    id={skill_id}  name={entry['name']}")
            click.echo(f"    summary={entry['summary'][:60]}...")
        else:
            target = skills_path / filename
            if target.exists() and not force:
                click.echo(
                    f"  {click.style('⚠', fg='yellow')} {target} 已存在，跳过（使用 --force 强制覆盖）"
                )
                continue
            target.write_text(content, encoding="utf-8")
            click.echo(f"  {click.style('✓', fg='green')} {target}")
            new_entries.append(entry)

    if dry_run:
        click.echo(f"\n{click.style('[dry-run]', fg='yellow')} 未写入任何文件")
        return

    if new_entries:
        click.echo("")
        _append_skills_to_yaml(config, new_entries)
        click.echo("\n下一步：")
        click.echo(f"  export SKILLS_ROOT={skills_path.resolve()}")
        click.echo("  skills-orchestrator build")
