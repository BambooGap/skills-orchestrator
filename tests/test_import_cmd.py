"""Tests for import command — all network calls mocked, no real GitHub access."""

from __future__ import annotations

from unittest.mock import patch

import click
import pytest
import yaml
from click.testing import CliRunner

from skills_orchestrator.cli.import_cmd import (
    MAX_IMPORT_BYTES,
    _validate_github_url,
    _validate_import_filename,
    _github_url_to_parts,
    _fetch_github_skills,
    _fetch_raw,
    _validate_importable_markdown,
)
from skills_orchestrator.cli.helpers import _slugify, _parse_frontmatter
from skills_orchestrator.main import _parse_context, cli


# ═══════════════════════════════════════════════════════════════
# _validate_github_url
# ═══════════════════════════════════════════════════════════════


class TestValidateGithubUrl:
    def test_github_com_allowed(self):
        assert _validate_github_url("https://github.com/user/repo") is True

    def test_raw_githubusercontent_allowed(self):
        assert (
            _validate_github_url("https://raw.githubusercontent.com/user/repo/main/skill.md")
            is True
        )

    def test_api_github_com_rejected_as_user_source(self):
        assert _validate_github_url("https://api.github.com/repos/user/repo/contents/") is False

    def test_http_github_rejected(self):
        assert _validate_github_url("http://github.com/user/repo") is False

    def test_evil_com_rejected(self):
        assert _validate_github_url("https://evil.com/user/repo") is False

    def test_localhost_rejected(self):
        assert _validate_github_url("http://127.0.0.1:8080/") is False

    def test_github_subdomain_rejected(self):
        """Subdomains of github.com that are not whitelisted should be rejected."""
        assert _validate_github_url("https://attacks.github.com/") is False

    def test_empty_url_rejected(self):
        assert _validate_github_url("") is False

    def test_non_url_rejected(self):
        assert _validate_github_url("not-a-url") is False

    def test_userinfo_rejected(self):
        assert _validate_github_url("https://token@github.com/user/repo") is False

    def test_secret_query_rejected(self):
        assert _validate_github_url("https://github.com/user/repo?token=secret") is False

    def test_fragment_rejected(self):
        assert _validate_github_url("https://github.com/user/repo#secret") is False


# ═══════════════════════════════════════════════════════════════
# _github_url_to_parts
# ═══════════════════════════════════════════════════════════════


class TestGithubUrlToParts:
    def test_repo_root(self):
        owner, repo, ref, path = _github_url_to_parts("https://github.com/user/repo")
        assert owner == "user"
        assert repo == "repo"
        assert ref is None
        assert path == ""

    def test_tree_url(self):
        owner, repo, ref, path = _github_url_to_parts(
            "https://github.com/user/repo/tree/main/skills"
        )
        assert owner == "user"
        assert repo == "repo"
        assert ref == "main"
        assert path == "skills"

    def test_blob_url(self):
        owner, repo, ref, path = _github_url_to_parts(
            "https://github.com/user/repo/blob/develop/skills/test.md"
        )
        assert owner == "user"
        assert repo == "repo"
        assert ref == "develop"
        assert path == "skills/test.md"

    def test_trailing_slash(self):
        owner, repo, ref, path = _github_url_to_parts("https://github.com/user/repo/")
        assert owner == "user"
        assert repo == "repo"
        assert ref is None
        assert path == ""

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="无法解析 GitHub URL"):
            _github_url_to_parts("https://not-github.com/user/repo")


# ═══════════════════════════════════════════════════════════════
# _slugify
# ═══════════════════════════════════════════════════════════════


class TestSlugify:
    def test_normal_text(self):
        assert _slugify("My Cool Skill") == "my-cool-skill"

    def test_chinese_text(self):
        result = _slugify("代码风格规范")
        assert "代码风格规范" in result or "代码" in result

    def test_pure_special_chars(self):
        """Pure special chars should fall back to stable hash ID."""
        result = _slugify("---")
        assert result.startswith("skill-")
        # Deterministic: same input → same output
        assert _slugify("---") == result

    def test_empty_string(self):
        """Empty string should fall back to stable hash ID."""
        result = _slugify("")
        assert result.startswith("skill-")
        assert _slugify("") == result

    def test_deterministic(self):
        """Same input must always produce the same output."""
        assert _slugify("test-name") == _slugify("test-name")

    def test_alphanumeric_preserved(self):
        assert _slugify("hello-world-123") == "hello-world-123"


# ═══════════════════════════════════════════════════════════════
# _parse_frontmatter
# ═══════════════════════════════════════════════════════════════


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nid: test-skill\nname: Test\nsummary: A test\n---\nBody text"
        meta = _parse_frontmatter(content)
        assert meta["id"] == "test-skill"
        assert meta["name"] == "Test"
        assert meta["summary"] == "A test"

    def test_description_alias_to_summary(self):
        """description field should be mapped to summary if summary missing."""
        content = "---\nname: Test\ndescription: From description\n---\nBody"
        meta = _parse_frontmatter(content)
        assert meta["summary"] == "From description"

    def test_tags_as_comma_string(self):
        content = "---\nname: Test\ntags: git, workflow, code\n---\nBody"
        meta = _parse_frontmatter(content)
        assert meta["tags"] == ["git", "workflow", "code"]

    def test_no_frontmatter_infers_from_heading(self):
        content = "# My Skill\n\nThis is the description of my skill."
        meta = _parse_frontmatter(content)
        assert meta["name"] == "My Skill"
        assert "description" in meta or "summary" in meta

    def test_no_frontmatter_no_heading(self):
        """Markdown with no frontmatter and no heading still returns a dict."""
        content = "Just some text without heading"
        meta = _parse_frontmatter(content)
        assert isinstance(meta, dict)

    def test_invalid_yaml_frontmatter_falls_back(self):
        """Malformed YAML in frontmatter should fall back to inference."""
        content = "---\nname: [bad yaml\n---\nBody"
        meta = _parse_frontmatter(content)
        # Should not crash; falls back to heading/para inference
        assert isinstance(meta, dict)

    def test_empty_content(self):
        """Empty content should return empty dict, not crash."""
        meta = _parse_frontmatter("")
        assert isinstance(meta, dict)


# ═══════════════════════════════════════════════════════════════
# _parse_context — path traversal
# ═══════════════════════════════════════════════════════════════


class TestParseContext:
    def test_json_string(self):
        result = _parse_context('{"key": "value"}')
        assert result == {"key": "value"}

    def test_path_traversal_rejected(self):
        """@/etc/passwd should be rejected — file must be within cwd."""
        with pytest.raises(click.BadParameter, match="安全限制"):
            _parse_context("@/etc/passwd")

    def test_relative_file_in_cwd(self, tmp_path, monkeypatch):
        """A file within cwd should be accepted."""
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "ctx.json"
        test_file.write_text('{"ok": true}')
        result = _parse_context(f"@{test_file}")
        assert result == {"ok": True}


# ═══════════════════════════════════════════════════════════════
# _fetch_github_skills — blob URL, directory, errors (all mocked)
# ═══════════════════════════════════════════════════════════════


class TestFetchGithubSkills:
    @patch("skills_orchestrator.cli.import_cmd._fetch_raw")
    @patch("skills_orchestrator.cli.import_cmd._resolve_github_commit")
    def test_blob_url_single_file(self, mock_commit, mock_fetch):
        """blob URL should fetch a single file via raw.githubusercontent.com."""
        mock_commit.return_value = "a" * 40
        mock_fetch.return_value = "---\nid: my-skill\nname: My Skill\n---\nContent"
        results = _fetch_github_skills("https://github.com/user/repo/blob/main/skills/my-skill.md")
        assert len(results) == 1
        assert results[0].filename == "my-skill.md"
        assert results[0].provenance["source_commit"] == "a" * 40
        assert results[0].provenance["content_hash"].startswith("sha256:")
        mock_fetch.assert_called_once()
        call_url = mock_fetch.call_args[0][0]
        assert "raw.githubusercontent.com" in call_url
        assert "/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/" in call_url
        assert "/main/" not in call_url

    @patch("skills_orchestrator.cli.import_cmd._fetch_raw")
    @patch("skills_orchestrator.cli.import_cmd._gh_api")
    @patch("skills_orchestrator.cli.import_cmd._resolve_github_commit")
    def test_directory_listing_flat(self, mock_commit, mock_api, mock_fetch):
        """Directory URL should list .md files from GitHub API."""
        mock_commit.return_value = "b" * 40
        mock_api.return_value = [
            {
                "type": "file",
                "name": "skill1.md",
                "path": "skills/skill1.md",
                "download_url": "https://raw.githubusercontent.com/user/repo/main/skills/skill1.md",
            },
            {
                "type": "file",
                "name": "README.md",
                "path": "skills/README.md",
                "download_url": "https://raw.githubusercontent.com/user/repo/main/skills/README.md",
            },
            {"type": "dir", "name": ".hidden", "path": "skills/.hidden"},
        ]
        mock_fetch.return_value = "---\nid: s1\nname: S1\n---\nContent"
        results = _fetch_github_skills("https://github.com/user/repo/tree/main/skills")
        # Only skill1.md (README and .hidden dir should be skipped)
        assert len(results) == 1
        assert results[0].filename == "skill1.md"
        assert results[0].provenance["source_ref"] == "main"
        assert results[0].provenance["source_commit"] == "b" * 40
        assert mock_api.call_args[0][0] == ("repos/user/repo/contents/skills?ref=" + ("b" * 40))
        assert mock_fetch.call_args[0][0] == (
            "https://raw.githubusercontent.com/user/repo/" + ("b" * 40) + "/skills/skill1.md"
        )

    @patch("skills_orchestrator.cli.import_cmd._fetch_raw")
    @patch("skills_orchestrator.cli.import_cmd._gh_api")
    @patch("skills_orchestrator.cli.import_cmd._resolve_github_commit")
    @patch("skills_orchestrator.cli.import_cmd._resolve_github_default_branch")
    def test_repo_root_uses_default_branch(
        self, mock_default_branch, mock_commit, mock_api, mock_fetch
    ):
        mock_default_branch.return_value = "master"
        mock_commit.return_value = "9" * 40
        mock_api.return_value = [
            {
                "type": "file",
                "name": "skill.md",
                "path": "skill.md",
                "download_url": "https://raw.githubusercontent.com/user/repo/master/skill.md",
            }
        ]
        mock_fetch.return_value = "---\nid: s1\nname: S1\n---\nContent"

        results = _fetch_github_skills("https://github.com/user/repo")

        assert len(results) == 1
        assert results[0].provenance["source_ref"] == "master"
        assert results[0].provenance["source_commit"] == "9" * 40
        mock_default_branch.assert_called_once_with("user", "repo")
        mock_commit.assert_called_once_with("user", "repo", "master")
        assert mock_api.call_args[0][0] == "repos/user/repo/contents?ref=" + ("9" * 40)

    @patch("skills_orchestrator.cli.import_cmd._gh_api")
    def test_api_timeout(self, mock_api):
        """GitHub API timeout should raise RuntimeError with hint."""
        mock_api.side_effect = RuntimeError("GitHub API 请求失败")
        with pytest.raises(RuntimeError, match="GitHub API 请求失败"):
            _fetch_github_skills("https://github.com/user/repo/tree/main/skills")

    @patch("skills_orchestrator.cli.import_cmd._gh_api")
    def test_api_404_raises(self, mock_api):
        """404 from GitHub API should raise RuntimeError."""
        mock_api.side_effect = RuntimeError("GitHub API 请求失败: 404")
        with pytest.raises(RuntimeError):
            _fetch_github_skills("https://github.com/user/repo/tree/main/nonexistent")

    @patch("skills_orchestrator.cli.import_cmd._gh_api")
    @patch("skills_orchestrator.cli.import_cmd._resolve_github_commit")
    def test_non_list_api_response(self, mock_commit, mock_api):
        """API returning non-list should raise RuntimeError."""
        mock_commit.return_value = "e" * 40
        mock_api.return_value = {"message": "Not Found"}
        with pytest.raises(RuntimeError, match="API 返回格式异常"):
            _fetch_github_skills("https://github.com/user/repo/tree/main/skills")

    @patch("skills_orchestrator.cli.import_cmd._fetch_raw")
    @patch("skills_orchestrator.cli.import_cmd._gh_api")
    @patch("skills_orchestrator.cli.import_cmd._resolve_github_commit")
    def test_subdirectory_with_skill_md(self, mock_commit, mock_api, mock_fetch):
        """Subdirectory containing SKILL.md should be discovered."""
        mock_commit.return_value = "c" * 40
        # First call: root listing
        # Second call: subdirectory listing
        mock_api.side_effect = [
            [{"type": "dir", "name": "karpathy-guidelines", "path": "skills/karpathy-guidelines"}],
            [
                {
                    "type": "file",
                    "name": "SKILL.md",
                    "path": "skills/karpathy-guidelines/SKILL.md",
                    "download_url": "https://raw.githubusercontent.com/user/repo/main/skills/karpathy-guidelines/SKILL.md",
                }
            ],
        ]
        mock_fetch.return_value = "---\nid: karpathy\nname: Karpathy\n---\nContent"
        results = _fetch_github_skills("https://github.com/user/repo/tree/main/skills")
        assert len(results) == 1
        assert results[0].filename == "karpathy-guidelines.md"

    @patch("skills_orchestrator.cli.import_cmd._fetch_raw")
    @patch("skills_orchestrator.cli.import_cmd._gh_api")
    @patch("skills_orchestrator.cli.import_cmd._resolve_github_commit")
    def test_api_download_url_is_ignored(self, mock_commit, mock_api, mock_fetch):
        mock_commit.return_value = "d" * 40
        mock_api.return_value = [
            {
                "type": "file",
                "name": "skill.md",
                "path": "skills/skill.md",
                "download_url": "https://169.254.169.254/latest/meta-data/skill.md",
            }
        ]
        mock_fetch.return_value = "---\nid: safe\nname: Safe\n---\nContent"

        results = _fetch_github_skills("https://github.com/user/repo/tree/main/skills")

        assert len(results) == 1
        assert mock_fetch.call_args[0][0] == (
            "https://raw.githubusercontent.com/user/repo/" + ("d" * 40) + "/skills/skill.md"
        )

    @patch("skills_orchestrator.cli.import_cmd._gh_api")
    @patch("skills_orchestrator.cli.import_cmd._resolve_github_commit")
    def test_unsafe_api_path_is_skipped(self, mock_commit, mock_api):
        mock_commit.return_value = "d" * 40
        mock_api.return_value = [
            {
                "type": "file",
                "name": "skill.md",
                "path": "../skill.md",
                "download_url": "https://raw.githubusercontent.com/user/repo/main/skill.md",
            }
        ]

        assert _fetch_github_skills("https://github.com/user/repo/tree/main/skills") == []


class TestValidateImportFilename:
    @pytest.mark.parametrize("filename", ["../pwn.md", "sub/evil.md", "evil\\x.md", "bad\nname.md"])
    def test_rejects_path_like_names(self, filename):
        with pytest.raises(ValueError):
            _validate_import_filename(filename)

    def test_accepts_plain_markdown_filename(self):
        assert _validate_import_filename("safe-skill.md") == "safe-skill.md"


# ═══════════════════════════════════════════════════════════════
# _fetch_raw — timeout and error handling
# ═══════════════════════════════════════════════════════════════


class TestFetchRaw:
    class FakeResponse:
        def __init__(
            self,
            data: bytes,
            url: str = "https://raw.githubusercontent.com/user/repo/main/skill.md",
        ):
            self.data = data
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, size=-1):
            if size is None or size < 0:
                return self.data
            return self.data[:size]

        def geturl(self):
            return self.url

    def test_timeout_raises(self):
        """urllib timeout should propagate as exception."""
        with patch("skills_orchestrator.cli.import_cmd._NO_REDIRECT_OPENER.open") as mock_open:
            mock_open.side_effect = TimeoutError("connection timed out")
            with pytest.raises(TimeoutError):
                _fetch_raw("https://raw.githubusercontent.com/user/repo/main/skill.md")

    def test_404_raises(self):
        """HTTP 404 should propagate as exception."""
        import urllib.error

        with patch("skills_orchestrator.cli.import_cmd._NO_REDIRECT_OPENER.open") as mock_open:
            mock_open.side_effect = urllib.error.HTTPError(
                url="", code=404, msg="Not Found", hdrs=None, fp=None
            )
            with pytest.raises(urllib.error.HTTPError):
                _fetch_raw("https://raw.githubusercontent.com/user/repo/main/nonexistent.md")

    def test_oversized_content_rejected(self):
        """Remote markdown should be bounded to avoid untrusted large downloads."""
        data = b"a" * (MAX_IMPORT_BYTES + 2)
        with patch("skills_orchestrator.cli.import_cmd._NO_REDIRECT_OPENER.open") as mock_open:
            mock_open.return_value = self.FakeResponse(
                data, url="https://raw.githubusercontent.com/user/repo/main/large.md"
            )
            with pytest.raises(ValueError, match="超过大小限制"):
                _fetch_raw("https://raw.githubusercontent.com/user/repo/main/large.md")

    def test_non_utf8_content_rejected(self):
        """Binary or non-UTF-8 content should be rejected."""
        with patch("skills_orchestrator.cli.import_cmd._NO_REDIRECT_OPENER.open") as mock_open:
            mock_open.return_value = self.FakeResponse(
                b"\xff\xfe\x00\x00",
                url="https://raw.githubusercontent.com/user/repo/main/binary.md",
            )
            with pytest.raises(ValueError, match="有效 UTF-8"):
                _fetch_raw("https://raw.githubusercontent.com/user/repo/main/binary.md")

    def test_empty_content_rejected(self):
        """Empty remote markdown should be rejected before metadata inference."""
        with patch("skills_orchestrator.cli.import_cmd._NO_REDIRECT_OPENER.open") as mock_open:
            mock_open.return_value = self.FakeResponse(
                b" \n\t\n", url="https://raw.githubusercontent.com/user/repo/main/empty.md"
            )
            with pytest.raises(ValueError, match="导入内容为空"):
                _fetch_raw("https://raw.githubusercontent.com/user/repo/main/empty.md")


class TestValidateImportableMarkdown:
    def test_no_frontmatter_allowed(self):
        """No frontmatter remains valid when metadata can be inferred later."""
        _validate_importable_markdown("# My Skill\n\nUseful content.")

    def test_invalid_yaml_frontmatter_rejected(self):
        with pytest.raises(ValueError, match="frontmatter YAML 解析失败"):
            _validate_importable_markdown("---\nname: [bad yaml\n---\nBody")


class TestImportCliTrustMetadata:
    @patch("skills_orchestrator.cli.import_cmd._fetch_raw")
    @patch("skills_orchestrator.cli.import_cmd._resolve_github_commit")
    def test_raw_import_writes_observed_provenance(self, mock_commit, mock_fetch, tmp_path):
        commit = "f" * 40
        source_url = f"https://raw.githubusercontent.com/user/repo/{commit}/imported.md"
        mock_commit.return_value = commit
        mock_fetch.return_value = (
            "---\n"
            "id: imported-skill\n"
            "name: Imported Skill\n"
            "summary: Imported summary\n"
            "source: internal://attacker-controlled\n"
            "license: MIT\n"
            "provenance:\n"
            "  source_commit: attacker-controlled\n"
            "---\n"
            "# Imported\n"
        )
        config = tmp_path / "skills.yaml"
        skills_dir = tmp_path / "skills"
        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "import",
                source_url,
                "--skills-dir",
                str(skills_dir),
                "--config",
                str(config),
            ],
        )

        assert result.exit_code == 0
        payload = yaml.safe_load(config.read_text(encoding="utf-8"))
        entry = payload["skills"][0]
        assert entry["source"] == source_url
        assert entry["license"] == "MIT"
        assert entry["provenance"]["source_ref"] == commit
        assert entry["provenance"]["source_commit"] == commit
        assert entry["provenance"]["source_commit"] != "attacker-controlled"
        assert entry["provenance"]["content_hash"].startswith("sha256:")

    def test_raw_import_rejects_mutable_branch_ref(self, tmp_path):
        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "import",
                "https://raw.githubusercontent.com/user/repo/main/imported.md",
                "--skills-dir",
                str(tmp_path / "skills"),
                "--config",
                str(tmp_path / "skills.yaml"),
            ],
        )

        assert result.exit_code == 1
        assert "完整 commit SHA" in result.output

    def test_rejected_secret_url_does_not_echo_token(self, tmp_path):
        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "import",
                "https://github.com/user/repo?token=supersecret",
                "--skills-dir",
                str(tmp_path / "skills"),
                "--config",
                str(tmp_path / "skills.yaml"),
            ],
        )

        assert result.exit_code == 1
        assert "supersecret" not in result.output


# ═══════════════════════════════════════════════════════════════
# _slugify — dangerous filename
# ═══════════════════════════════════════════════════════════════


class TestSlugifyDangerousFilename:
    def test_path_traversal_dots_stripped(self):
        """Paths with .. should be sanitized, not produce traversal-friendly ids."""
        result = _slugify("../../etc/passwd")
        # Should not start with .. or contain path separators
        assert not result.startswith("..")
        assert "//" not in result

    def test_null_bytes_stripped(self):
        """Null bytes in name should be sanitized."""
        result = _slugify("evil\x00name")
        assert "\x00" not in result

    def test_absolute_path_stripped(self):
        """Absolute path as name should be sanitized."""
        result = _slugify("/etc/shadow")
        assert not result.startswith("/")


# ═══════════════════════════════════════════════════════════════
# _parse_frontmatter — no title and no summary edge cases
# ═══════════════════════════════════════════════════════════════


class TestParseFrontmatterNoMetadata:
    def test_no_frontmatter_no_heading_no_paragraph(self):
        """Markdown with no frontmatter, no heading, no paragraph → still returns dict, no crash."""
        content = "   \n\n   \n"
        meta = _parse_frontmatter(content)
        assert isinstance(meta, dict)

    def test_no_frontmatter_heading_only_no_summary(self):
        """Markdown with heading but no body text → name inferred, no summary."""
        content = "# Just A Title\n"
        meta = _parse_frontmatter(content)
        assert meta.get("name") == "Just A Title"
        # summary may be absent — that's OK, metadata inference is best-effort

    def test_frontmatter_with_no_title_and_no_summary(self):
        """Frontmatter with neither name/title nor summary → returns dict without those keys."""
        content = "---\ntags: [test]\n---\nSome body text"
        meta = _parse_frontmatter(content)
        assert isinstance(meta, dict)
        assert "tags" in meta
        # name and summary may be absent — that's OK
