from pathlib import Path

import pytest

from skills_orchestrator.security import (
    console_safe_symbol,
    console_safe_text,
    parse_int_in_range,
    safe_child_path,
    subprocess_text_kwargs,
    validate_identifier,
    validate_skill_id,
    validate_path_within_root,
)


def test_validate_identifier_accepts_safe_values():
    assert validate_identifier("full-dev", "pipeline_id") == "full-dev"
    assert validate_identifier("run_123", "run_id") == "run_123"


def test_validate_identifier_rejects_path_traversal():
    with pytest.raises(ValueError, match="非法"):
        validate_identifier("../evil", "pipeline_id")


def test_validate_identifier_rejects_slashes_and_empty_values():
    for value in ("", "a/b", "/absolute", "a.b"):
        with pytest.raises(ValueError, match="非法"):
            validate_identifier(value, "id")


def test_validate_skill_id_allows_chinese_ids():
    assert validate_skill_id("安全重构") == "安全重构"
    assert validate_skill_id("code-style_测试") == "code-style_测试"


def test_validate_skill_id_rejects_path_traversal_and_punctuation():
    for value in ("../evil", "a/b", "/absolute", "a.b", "bad:name"):
        with pytest.raises(ValueError, match="非法"):
            validate_skill_id(value)


def test_validate_path_within_root_rejects_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="路径逃逸"):
        validate_path_within_root(outside, root)


def test_safe_child_path_rejects_parent_segments(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(ValueError, match="路径逃逸"):
        safe_child_path(root, "..", "outside.txt")


def test_parse_int_in_range_defaults_and_clamps():
    assert parse_int_in_range(None, "top_k", default=5, minimum=1, maximum=20) == 5
    assert parse_int_in_range(999, "top_k", default=5, minimum=1, maximum=20) == 20
    assert parse_int_in_range(0, "top_k", default=5, minimum=1, maximum=20) == 1


def test_parse_int_in_range_rejects_invalid_values():
    for value in ("many", True, Path(".")):
        with pytest.raises(ValueError, match="top_k"):
            parse_int_in_range(value, "top_k", default=5, minimum=1, maximum=20)


def test_subprocess_text_kwargs_force_utf8_replace():
    kwargs = subprocess_text_kwargs()
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"


def test_console_safe_symbol_uses_ascii_fallback_for_non_utf8(monkeypatch):
    class Stream:
        encoding = "cp936"

    monkeypatch.setattr("sys.stdout", Stream())
    assert console_safe_symbol("✓", "OK") == "OK"


def test_console_safe_text_replaces_common_glyphs_for_non_utf8(monkeypatch):
    class Stream:
        encoding = "gbk"

    monkeypatch.setattr("sys.stdout", Stream())
    assert console_safe_text("✓ a → b ⚠") == "OK a -> b !"


def test_console_safe_text_replaces_unencodable_glyphs_for_non_utf8(monkeypatch):
    class Stream:
        encoding = "gbk"

    monkeypatch.setattr("sys.stdout", Stream())
    output = console_safe_text("部署 🛠️ — •")
    assert "部署" in output
    assert "—" not in output
    assert "•" not in output
    output.encode("gbk")
