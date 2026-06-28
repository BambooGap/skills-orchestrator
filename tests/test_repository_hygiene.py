from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dual_license_metadata_and_files_are_present():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["license"] == "MIT OR Apache-2.0"
    assert all(
        not classifier.startswith("License ::")
        for classifier in pyproject["project"]["classifiers"]
    )

    license_notice = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License, Version 2.0" in license_notice
    assert "MIT License" in license_notice
    assert (ROOT / "LICENSE-MIT").read_text(encoding="utf-8").startswith("MIT License")
    assert "Apache License" in (ROOT / "LICENSE-APACHE").read_text(encoding="utf-8")


def test_community_health_files_exist_for_external_review():
    expected = [
        "CODE_OF_CONDUCT.md",
        "SUPPORT.md",
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "MAINTAINERS.md",
        "SECURITY.md",
        "THIRD_PARTY_NOTICES.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/CODEOWNERS",
    ]

    for relative in expected:
        path = ROOT / relative
        assert path.exists(), relative
        assert path.read_text(encoding="utf-8").strip(), relative


def test_readme_points_to_dual_license_and_support_surfaces():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "MIT OR Apache-2.0" in readme
    assert "[Support](SUPPORT.md)" in readme
    assert "[Code of Conduct](CODE_OF_CONDUCT.md)" in readme
    assert "[Third-party Notices](THIRD_PARTY_NOTICES.md)" in readme
