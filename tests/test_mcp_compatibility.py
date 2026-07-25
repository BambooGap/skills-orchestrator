from __future__ import annotations

import json

from scripts import report_mcp_versions


def test_collect_versions_omits_packages_that_are_not_installed(monkeypatch):
    versions = {"mcp": "1.28.1", "starlette": "1.3.1", "sse-starlette": "3.4.5"}

    def fake_version(package: str) -> str:
        if package not in versions:
            raise report_mcp_versions.metadata.PackageNotFoundError(package)
        return versions[package]

    monkeypatch.setattr(report_mcp_versions.metadata, "version", fake_version)

    assert report_mcp_versions.collect_versions() == versions


def test_main_prints_stable_json(monkeypatch, capsys):
    monkeypatch.setattr(
        report_mcp_versions,
        "collect_versions",
        lambda: {"starlette": "1.3.1", "mcp": "1.28.1"},
    )

    assert report_mcp_versions.main() == 0
    assert json.loads(capsys.readouterr().out) == {
        "mcp": "1.28.1",
        "starlette": "1.3.1",
    }
