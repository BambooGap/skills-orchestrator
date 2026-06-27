from pathlib import Path

from scripts.check_docker_base_digest import find_unpinned_base_images


def test_docker_base_digest_check_flags_unpinned_image(tmp_path: Path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.12-slim\n", encoding="utf-8")

    issues = find_unpinned_base_images(dockerfile)

    assert len(issues) == 1
    assert "not digest-pinned" in issues[0]


def test_docker_base_digest_check_accepts_sha256_pinned_image(tmp_path: Path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        "FROM python:3.12-slim@sha256:" + "a" * 64 + "\n",
        encoding="utf-8",
    )

    assert find_unpinned_base_images(dockerfile) == []


def test_docker_base_digest_check_accepts_scratch(tmp_path: Path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM scratch\n", encoding="utf-8")

    assert find_unpinned_base_images(dockerfile) == []
