"""import command — 从 GitHub 导入 skill 文件并注册到 skills.yaml"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from urllib.parse import quote, urlparse

import click
import yaml

from skills_orchestrator.security import (
    console_safe_symbol,
    console_safe_text,
    safe_child_path,
    safe_subprocess_env,
    subprocess_text_kwargs,
)

from .helpers import (
    _append_skills_to_yaml,
    _err,
    _parse_frontmatter,
    _slugify,
    _warn,
)


# ─── GitHub import helpers ────────────────────────────────────────


MAX_IMPORT_BYTES = 2 * 1024 * 1024
GITHUB_SOURCE_HOSTS = {"github.com", "raw.githubusercontent.com"}


@dataclass(frozen=True)
class ImportCandidate:
    filename: str
    content: str
    provenance: dict[str, str]


def _gh_api(api_path: str) -> object:
    """优先用 gh CLI（已认证，无限速），失败则回退到 urllib。"""
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "api", api_path],
            capture_output=True,
            **subprocess_text_kwargs(),
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
        _canonical_github_url(url)
        return True
    except Exception:
        return False


def _canonical_github_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in GITHUB_SOURCE_HOSTS:
        raise ValueError("安全限制：仅支持 HTTPS GitHub URL")
    if parsed.username or parsed.password:
        raise ValueError("安全限制：GitHub URL 不允许包含 userinfo")
    if parsed.query or parsed.fragment:
        raise ValueError("安全限制：GitHub URL 不允许包含 query 或 fragment")
    return parsed._replace(netloc=parsed.hostname, query="", fragment="").geturl()


def _validate_raw_github_url(url: str) -> str:
    canonical = _canonical_github_url(url)
    if urlparse(canonical).hostname != "raw.githubusercontent.com":
        raise ValueError("安全限制：下载 URL 必须来自 raw.githubusercontent.com")
    return canonical


def _validate_import_filename(filename: str) -> str:
    name = Path(filename).name
    if (
        name != filename
        or "\\" in filename
        or "\x00" in filename
        or any(char in filename for char in "\r\n")
    ):
        raise ValueError(f"不安全的导入文件名: {filename!r}")
    if not name.endswith(".md"):
        raise ValueError("导入文件名必须以 .md 结尾")
    return name


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401, ANN001
        raise ValueError("安全限制：导入下载不允许 HTTP redirect")


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def _decode_markdown_bytes(data: bytes, source: str = "") -> str:
    if len(data) > MAX_IMPORT_BYTES:
        raise ValueError(f"导入内容超过大小限制（最大 {MAX_IMPORT_BYTES // 1024 // 1024} MB）")

    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        label = f" {source}" if source else ""
        raise ValueError(f"导入内容{label}不是有效 UTF-8，可能是二进制文件") from exc

    if not content.strip():
        raise ValueError("导入内容为空")

    return content


def _validate_importable_markdown(content: str) -> None:
    """校验远程导入内容的安全边界，保持无 frontmatter 推断兼容。"""
    if not content.startswith("---"):
        return

    end = content.find("\n---", 3)
    if end == -1:
        raise ValueError("frontmatter 缺少结束分隔符")

    frontmatter = content[3:end].strip()
    try:
        yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"frontmatter YAML 解析失败: {exc}") from exc


def _fetch_raw(url: str) -> str:
    canonical = _validate_raw_github_url(url)
    req = urllib.request.Request(canonical, headers={"User-Agent": "skills-orchestrator/1.0"})
    with _NO_REDIRECT_OPENER.open(req, timeout=15) as resp:
        final_url = getattr(resp, "url", None) or resp.geturl()
        if final_url != canonical:
            raise ValueError("安全限制：导入下载 URL 发生了变化")
        content = _decode_markdown_bytes(resp.read(MAX_IMPORT_BYTES + 1), canonical)
        _validate_importable_markdown(content)
        return content


def _github_url_to_parts(source: str) -> tuple[str, str, str | None, str]:
    """解析 GitHub URL，返回 (owner, repo, ref, path)。"""
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)(?:/(tree|blob)/([^/]+)(/.*)?)?",
        source.rstrip("/"),
    )
    if not m:
        raise ValueError("无法解析 GitHub URL")
    owner, repo = m.group(1), m.group(2)
    ref = m.group(4)
    path = (m.group(5) or "").lstrip("/")
    return owner, repo, ref, path


def _raw_url_to_parts(source: str) -> tuple[str, str, str, str]:
    parsed = urlparse(source)
    parts = parsed.path.strip("/").split("/", 3)
    if len(parts) != 4:
        raise ValueError(f"无法解析 raw.githubusercontent.com URL: {source}")
    owner, repo, ref, path = parts
    if not _is_full_sha(ref):
        raise ValueError(
            "raw.githubusercontent.com 导入必须使用完整 commit SHA，不能使用可变分支名"
        )
    return owner, repo, ref, path


def _is_full_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", value))


def _resolve_github_default_branch(owner: str, repo: str) -> str:
    data = _gh_api(f"repos/{owner}/{repo}")
    if not isinstance(data, dict) or not data.get("default_branch"):
        raise RuntimeError(f"GitHub 默认分支解析失败: {owner}/{repo}")
    return str(data["default_branch"])


def _resolve_github_commit(owner: str, repo: str, ref: str) -> str:
    data = _gh_api(f"repos/{owner}/{repo}/commits/{ref}")
    if not isinstance(data, dict) or not data.get("sha"):
        raise RuntimeError(f"GitHub commit 解析失败: {owner}/{repo}@{ref}")
    return str(data["sha"])


def _resolve_source_ref(owner: str, repo: str, ref: str | None) -> tuple[str, str]:
    source_ref = ref or _resolve_github_default_branch(owner, repo)
    return source_ref, _resolve_github_commit(owner, repo, source_ref)


def _validate_repo_path(path: str) -> str:
    if "\\" in path or "\x00" in path or any(char in path for char in "\r\n"):
        raise ValueError(f"不安全的 GitHub 仓库路径: {path!r}")
    parts = [part for part in path.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise ValueError(f"不安全的 GitHub 仓库路径: {path!r}")
    return "/".join(parts)


def _raw_url_for_commit(owner: str, repo: str, commit: str, repo_path: str) -> str:
    safe_path = quote(_validate_repo_path(repo_path), safe="/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{commit}/{safe_path}"


def _contents_api_path(owner: str, repo: str, repo_path: str, commit: str) -> str:
    safe_path = quote(repo_path.strip("/"), safe="/")
    if not safe_path:
        return f"repos/{owner}/{repo}/contents?ref={commit}"
    return f"repos/{owner}/{repo}/contents/{safe_path}?ref={commit}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _provenance(
    *,
    source_url: str,
    source_ref: str,
    source_commit: str,
    content: str,
) -> dict[str, str]:
    return {
        "source_url": source_url,
        "source_ref": source_ref,
        "source_commit": source_commit,
        "content_hash": "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "fetched_at": _now_iso(),
    }


def _fetch_github_skills(source: str) -> list[ImportCandidate]:
    """返回 ImportCandidate 列表。

    支持两种仓库结构：
    1. 扁平：目录下直接放 *.md
    2. 子目录：每个 skill 一个子目录，内含 SKILL.md（如 karpathy-skills 格式）
    """
    owner, repo, requested_ref, path = _github_url_to_parts(source)
    source_ref, commit = _resolve_source_ref(owner, repo, requested_ref)

    # 单文件（blob URL）
    if "/blob/" in source:
        raw_url = _raw_url_for_commit(owner, repo, commit, path)
        filename = _validate_import_filename(Path(path).name)
        content = _fetch_raw(raw_url)
        return [
            ImportCandidate(
                filename=filename,
                content=content,
                provenance=_provenance(
                    source_url=raw_url,
                    source_ref=source_ref,
                    source_commit=commit,
                    content=content,
                ),
            )
        ]

    # 目录或仓库根
    api_path = _contents_api_path(owner, repo, path, commit)

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
                filename = _validate_import_filename(str(item["name"]))
                raw_url = _raw_url_for_commit(owner, repo, commit, str(item["path"]))
                content = _fetch_raw(raw_url)
                results.append(
                    ImportCandidate(
                        filename=filename,
                        content=content,
                        provenance=_provenance(
                            source_url=raw_url,
                            source_ref=source_ref,
                            source_commit=commit,
                            content=content,
                        ),
                    )
                )
                click.echo(console_safe_text(f"  {console_safe_symbol('✓', 'OK')} {filename}"))
            except Exception as e:
                click.echo(_warn(f"跳过 {item['name']}: {e}"))

        # 子目录结构：进入子目录找 SKILL.md（karpathy-skills 格式）
        elif item.get("type") == "dir" and not item["name"].startswith("."):
            sub_api_path = _contents_api_path(owner, repo, str(item["path"]), commit)
            try:
                sub_items = _gh_api(sub_api_path)
                if isinstance(sub_items, list):
                    for sub in sub_items:
                        if sub.get("type") == "file" and sub["name"].upper() == "SKILL.MD":
                            raw_url = _raw_url_for_commit(owner, repo, commit, str(sub["path"]))
                            content = _fetch_raw(raw_url)
                            filename = _validate_import_filename(f"{item['name']}.md")
                            results.append(
                                ImportCandidate(
                                    filename=filename,
                                    content=content,
                                    provenance=_provenance(
                                        source_url=raw_url,
                                        source_ref=source_ref,
                                        source_commit=commit,
                                        content=content,
                                    ),
                                )
                            )
                            arrow = console_safe_symbol("→", "->")
                            click.echo(
                                console_safe_text(
                                    f"  {console_safe_symbol('✓', 'OK')} "
                                    f"{item['name']}/SKILL.md {arrow} {filename}"
                                )
                            )
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

    try:
        if not _validate_github_url(source):
            raise ValueError(
                "安全限制：只支持 GitHub URL (github.com, raw.githubusercontent.com)\n"
                "支持的来源：GitHub repo / 目录 / 单文件，或 raw.githubusercontent.com 直链"
            )

        source = _canonical_github_url(source)
        click.echo(f"来源: {source}\n")

        parsed_host = urlparse(source).hostname or ""
        if parsed_host == "raw.githubusercontent.com":
            if not source.endswith(".md"):
                raise ValueError("raw.githubusercontent.com 链接必须以 .md 结尾")
            owner, repo, ref, _path = _raw_url_to_parts(source)
            commit = _resolve_github_commit(owner, repo, ref)
            filename = _validate_import_filename(source.rsplit("/", 1)[-1])
            content = _fetch_raw(source)
            files = [
                ImportCandidate(
                    filename=filename,
                    content=content,
                    provenance=_provenance(
                        source_url=source,
                        source_ref=ref,
                        source_commit=commit,
                        content=content,
                    ),
                )
            ]
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
    for candidate in files:
        meta = _parse_frontmatter(candidate.content)
        stem = Path(candidate.filename).stem
        skill_id = meta.get("id", _slugify(stem))
        entry = {
            "id": skill_id,
            "name": meta.get("name", stem.replace("-", " ").title()),
            "path": f"${{SKILLS_ROOT}}/{candidate.filename}",
            "summary": meta.get("summary", f"从 {source} 导入"),
            "tags": meta.get("tags", []),
            "load_policy": meta.get("load_policy", "free"),
            "priority": int(meta.get("priority", 50)),
            "zones": ["default"],
            "conflict_with": [],
            "source": candidate.provenance["source_url"],
            "license": meta.get("license", ""),
            "provenance": candidate.provenance,
        }

        if dry_run:
            click.echo(f"  {click.style('[dry-run]', fg='yellow')} {candidate.filename}")
            click.echo(f"    id={skill_id}  name={entry['name']}")
            click.echo(f"    summary={entry['summary'][:60]}...")
            click.echo(f"    source_commit={candidate.provenance['source_commit'][:12]}")
        else:
            target = safe_child_path(skills_path, candidate.filename)
            if target.exists() and not force:
                warning = console_safe_symbol("⚠", "!")
                click.echo(
                    console_safe_text(
                        f"  {click.style(warning, fg='yellow')} "
                        f"{target} 已存在，跳过（使用 --force 强制覆盖）"
                    )
                )
                continue
            target.write_text(candidate.content, encoding="utf-8")
            click.echo(
                console_safe_text(
                    f"  {click.style(console_safe_symbol('✓', 'OK'), fg='green')} {target}"
                )
            )
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
