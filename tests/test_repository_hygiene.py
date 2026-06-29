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
    assert license_notice.startswith("MIT License")
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


def test_external_pilot_authorization_surfaces_are_present():
    outreach = ROOT / "docs/pilot-outreach.md"
    issue_template = ROOT / ".github/ISSUE_TEMPLATE/external_pilot_request.md"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert outreach.exists()
    assert issue_template.exists()

    outreach_text = outreach.read_text(encoding="utf-8")
    issue_text = issue_template.read_text(encoding="utf-8")

    assert "Private technical pilot" in outreach_text
    assert "Public adopter / case study" in outreach_text
    assert "Declined / no follow-up" in outreach_text
    assert "public_listing.status" in outreach_text
    assert "No public case study, quote, logo, or adopter listing" in issue_text
    assert "Not interested. Please close this request and do not follow up." in issue_text
    assert "[Authorized Pilot Outreach](docs/pilot-outreach.md)" in readme


def test_readme_points_to_dual_license_and_support_surfaces():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "MIT OR Apache-2.0" in readme
    assert "License-MIT%20OR%20Apache--2.0-blue.svg)](#license)" in readme
    assert "The top-level `LICENSE` keeps GitHub license detection" in readme
    assert "[`LICENSE-APACHE`](LICENSE-APACHE)" in readme
    assert "[Support](SUPPORT.md)" in readme
    assert "[Code of Conduct](CODE_OF_CONDUCT.md)" in readme
    assert "[Third-party Notices](THIRD_PARTY_NOTICES.md)" in readme


def test_readme_exposes_release_verification_and_slsa_boundaries():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "GitHub latest release" in readme
    assert "https://github.com/BambooGap/skills-orchestrator/releases/latest" in readme
    assert "https://pypi.org/project/skills-orchestrator/" in readme
    assert (
        "https://github.com/BambooGap/skills-orchestrator/pkgs/container/skills-orchestrator"
        in readme
    )
    assert "actions/workflows/post-release-smoke.yml" in readme
    assert "[Supply Chain Verification](docs/supply-chain-verification.md)" in readme
    assert "not formal SLSA level certification" in readme
    assert "SLSA Build L3+" in readme
    assert "[Production Adoption](docs/production-adoption.md)" in readme
