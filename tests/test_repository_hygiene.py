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


def test_external_adoption_authorization_surfaces_are_present():
    outreach = ROOT / "docs/adoption-authorization.md"
    issue_template = ROOT / ".github/ISSUE_TEMPLATE/external_adoption_request.md"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert outreach.exists()
    assert issue_template.exists()

    outreach_text = outreach.read_text(encoding="utf-8")
    issue_text = issue_template.read_text(encoding="utf-8")

    assert "Private technical adoption" in outreach_text
    assert "Public adopter / case study" in outreach_text
    assert "Declined / no follow-up" in outreach_text
    assert "public_listing.status" in outreach_text
    assert "No public case study, quote, logo, or adopter listing" in issue_text
    assert "Not interested. Please close this request and do not follow up." in issue_text
    assert "[Adoption Authorization](docs/adoption-authorization.md)" in readme


def test_readme_points_to_dual_license_and_support_surfaces():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "MIT OR Apache-2.0" in readme
    assert "License-MIT%20OR%20Apache--2.0-blue.svg)](#license)" in readme
    assert "[MIT](LICENSE)" in readme
    assert "[Apache-2.0](LICENSE-APACHE)" in readme
    assert "[Support](SUPPORT.md)" in readme
    assert "[Code of Conduct](CODE_OF_CONDUCT.md)" in readme
    assert "[Third-party Notices](THIRD_PARTY_NOTICES.md)" in readme


def test_readme_stays_focused_as_a_repository_entrypoint():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert len(readme.splitlines()) <= 300
    assert "## Quick start" in readme
    assert "## What it solves" in readme
    assert "## Documentation" in readme
    assert "[Documentation Index](docs/INDEX.md)" in readme


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
    assert "actions/workflows/release-integrity.yml" in readme
    assert "a Git tag or the version in the source tree is not a public-release claim" in readme
    assert "`v4.8.50` on PyPI" not in readme
    assert "[Supply Chain Verification](docs/supply-chain-verification.md)" in readme
    assert "它不是正式 SLSA 等级认证" in readme
    assert "it is not formal SLSA level certification" not in readme
    assert "SLSA Build L3+" in readme
    assert "[Production Adoption](docs/production-adoption.md)" in readme


def test_release_integrity_runs_the_reusable_public_artifact_smoke():
    workflow = (ROOT / ".github" / "workflows" / "release-integrity.yml").read_text(
        encoding="utf-8"
    )
    smoke = (ROOT / ".github" / "workflows" / "post-release-smoke.yml").read_text(encoding="utf-8")

    assert "types: [published]" in workflow
    assert "uses: ./.github/workflows/verify-release-tag.yml" in workflow
    assert "needs: verify-release-tag" in workflow
    assert "uses: ./.github/workflows/post-release-smoke.yml" in workflow
    assert 'retries: "30"' in workflow
    assert "--clobber" not in workflow
    assert "actions/attest-build-provenance@" in workflow
    assert "workflow_call:" in smoke


def test_release_publishers_require_a_github_verified_annotated_tag():
    verifier = (ROOT / ".github" / "workflows" / "verify-release-tag.yml").read_text(
        encoding="utf-8"
    )
    publish = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    ghcr = (ROOT / ".github" / "workflows" / "ghcr.yml").read_text(encoding="utf-8")

    assert "workflow_call:" in verifier
    assert "workflow_dispatch:" in verifier
    assert "Require a GitHub-verified annotated tag" in verifier
    assert "ref_type" in verifier
    assert ".verification.verified" in verifier
    assert ".verification.reason" in verifier
    assert "target_type" in verifier
    assert "target_sha" in verifier

    for workflow in (publish, ghcr):
        assert "uses: ./.github/workflows/verify-release-tag.yml" in workflow
        assert "needs: verify-release-tag" in workflow

    assert "ref: ${{ github.event.release.tag_name || inputs.version || github.sha }}" in ghcr
    assert 'source_sha="$(git rev-parse HEAD)"' in ghcr


def test_mcp_isolation_and_json_consumer_contracts_are_documented():
    install = (ROOT / "docs" / "install.md").read_text(encoding="utf-8")
    mcp = (ROOT / "docs" / "MCP_SERVER.md").read_text(encoding="utf-8")
    registry = (ROOT / "docs" / "registry-evidence.md").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "release-verification.md").read_text(encoding="utf-8")

    assert "pipx install" in install
    assert "uv tool install" in install
    assert "FastAPI `0.116.1`" in install
    assert "constraints-mcp.txt" in install
    assert "does not force a lower Starlette ceiling" in mcp
    assert "jq '.schema_version, .summary, .configs[].skills'" in registry
    assert "jq '.schema_version, .ledger.bundle_hash, (.files | length)'" in registry
    assert "schema validate" in registry
    assert "mcp-runtime-sbom.cdx.json" in release


def test_mcp_release_constraints_and_compatibility_matrix_are_retained():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    constraints = (ROOT / "constraints-mcp.txt").read_text(encoding="utf-8")
    all_constraints = (ROOT / "constraints.txt").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    smoke = (ROOT / ".github" / "workflows" / "post-release-smoke.yml").read_text(encoding="utf-8")
    integrity = (ROOT / ".github" / "workflows" / "release-integrity.yml").read_text(
        encoding="utf-8"
    )

    assert pyproject["project"]["optional-dependencies"]["mcp"] == ["mcp>=1.0,<2"]
    scoped_pins = {line for line in constraints.splitlines() if line and not line.startswith("#")}
    all_pins = {line for line in all_constraints.splitlines() if line and not line.startswith("#")}
    assert scoped_pins <= all_pins
    for dependency in ("mcp", "sse-starlette", "starlette"):
        assert any(pin.startswith(f"{dependency}==") for pin in scoped_pins)
    for profile in (
        "constrained",
        "minimum",
        "latest",
        "fastapi-current",
        "fastapi-old-unsupported",
    ):
        assert f"profile: {profile}" in ci
    assert 'python-version: "3.13"' in ci
    assert "mcp-test list_skills" in ci
    assert "fastapi==0.140.0" in ci
    assert "fastapi==0.116.1" in ci
    assert "--check-mcp-runtime" in smoke
    assert "--mcp-constraints constraints-mcp.txt" in smoke
    for asset in ("mcp-runtime-sbom.cdx.json", "constraints-mcp.txt"):
        assert asset in smoke
        assert asset in integrity


def test_post_release_evidence_is_bound_to_verified_tag_source():
    smoke = (ROOT / ".github" / "workflows" / "post-release-smoke.yml").read_text(encoding="utf-8")
    integrity = (ROOT / ".github" / "workflows" / "release-integrity.yml").read_text(
        encoding="utf-8"
    )

    assert "source_sha:" in smoke
    assert "required: true" in smoke
    assert "uses: ./.github/workflows/verify-release-tag.yml" in smoke
    assert "ref: ${{ needs.verify-release-tag.outputs.target_sha }}" in smoke
    assert '"$CALLER_SOURCE_SHA" != "$VERIFIED_TARGET_SHA"' in smoke
    assert 'checked_out_sha="$(git rev-parse HEAD)"' in smoke
    assert '"$checked_out_sha" != "$VERIFIED_TARGET_SHA"' in smoke
    assert "--verified-target-sha" in smoke
    assert "--checked-out-sha" in smoke
    assert "--constraints-sha256" in smoke
    assert "source_sha: ${{ needs.verify-release-tag.outputs.target_sha }}" in integrity
