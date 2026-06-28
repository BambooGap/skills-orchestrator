import json
from pathlib import Path

from click.testing import CliRunner

from skills_orchestrator.main import cli
from skills_orchestrator.schema_validation import validate_document
from skills_orchestrator.supply_chain import (
    build_container_image_sbom,
    build_slsa_readiness,
    verify_container_release,
)


def test_container_image_sbom_binds_to_digest():
    digest = "sha256:" + ("b" * 64)

    sbom = build_container_image_sbom(
        image="ghcr.io/bamboogap/skills-orchestrator",
        tag="v4.2.0",
        digest=digest,
        include_dependencies=False,
    )

    component = sbom["metadata"]["component"]
    assert component["type"] == "container"
    assert component["purl"].endswith(f"@{digest}")
    assert any(prop["value"] == digest for prop in component["properties"])


def test_container_release_cli_writes_schema_valid_artifacts(tmp_path):
    digest = "sha256:" + ("c" * 64)
    sbom_path = tmp_path / "container-sbom.cdx.json"
    provenance_path = tmp_path / "container-provenance.json"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "supply-chain",
            "container-release",
            "--image",
            "ghcr.io/bamboogap/skills-orchestrator",
            "--tag",
            "v4.2.0",
            "--digest",
            digest,
            "--repository",
            "BambooGap/skills-orchestrator",
            "--commit",
            "abc123",
            "--workflow-run-url",
            "https://github.com/BambooGap/skills-orchestrator/actions/runs/1",
            "--sbom-output",
            str(sbom_path),
            "--provenance-output",
            str(provenance_path),
            "--no-dependencies",
        ],
    )

    assert result.exit_code == 0
    assert validate_document("supply-chain-sbom", str(sbom_path)).valid is True
    assert validate_document("container-provenance", str(provenance_path)).valid is True
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["image"]["digest"] == digest
    assert provenance["attestations"]["provenance_subject"]["subject_digest"] == digest
    assert provenance["sbom"]["sha256"]


def test_slsa_readiness_report_is_schema_valid(tmp_path):
    digest = "sha256:" + ("e" * 64)

    report = build_slsa_readiness(
        release_version="4.8.26",
        repository="BambooGap/skills-orchestrator",
        image="ghcr.io/bamboogap/skills-orchestrator",
        digest=digest,
    )

    assert report["status"] == "readiness-mapped"
    assert report["subject"]["release"] == "v4.8.26"
    assert report["subject"]["digest"] == digest
    assert report["summary"]["formal_claim"] is False
    assert any(control["id"] == "build-l3.hardened-isolation" for control in report["controls"])
    output = tmp_path / "slsa-readiness.json"
    output.write_text(json.dumps(report), encoding="utf-8")
    assert validate_document("slsa-readiness", str(output)).valid is True


def test_slsa_readiness_cli_writes_json_report(tmp_path):
    output = tmp_path / "slsa-readiness.json"
    digest = "sha256:" + ("f" * 64)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "supply-chain",
            "slsa-readiness",
            "--version",
            "v4.8.26",
            "--digest",
            digest,
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "SLSA readiness report written" in result.output
    assert validate_document("slsa-readiness", str(output)).valid is True


def test_slsa_readiness_cli_rejects_invalid_digest():
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "supply-chain",
            "slsa-readiness",
            "--digest",
            "latest",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 1
    assert "sha256" in result.output


def test_container_release_cli_rejects_non_digest_subject(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "supply-chain",
            "container-release",
            "--image",
            "ghcr.io/bamboogap/skills-orchestrator",
            "--digest",
            "latest",
            "--sbom-output",
            str(tmp_path / "container-sbom.cdx.json"),
            "--provenance-output",
            str(tmp_path / "container-provenance.json"),
        ],
    )

    assert result.exit_code == 1
    assert "sha256" in result.output


def test_verify_container_release_passes_matching_provenance(tmp_path):
    digest = "sha256:" + ("d" * 64)
    sbom_path = tmp_path / "container-sbom.cdx.json"
    provenance_path = tmp_path / "container-provenance.json"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "supply-chain",
            "container-release",
            "--image",
            "ghcr.io/bamboogap/skills-orchestrator",
            "--tag",
            "v4.8.0",
            "--digest",
            digest,
            "--repository",
            "BambooGap/skills-orchestrator",
            "--commit",
            "def456",
            "--workflow-run-url",
            "https://github.com/BambooGap/skills-orchestrator/actions/runs/2",
            "--sbom-output",
            str(sbom_path),
            "--provenance-output",
            str(provenance_path),
            "--no-dependencies",
        ],
    )
    assert result.exit_code == 0

    report = verify_container_release(
        provenance_path=provenance_path,
        sbom_path=sbom_path,
        expected_image="ghcr.io/bamboogap/skills-orchestrator",
        expected_tag="v4.8.0",
        expected_digest=digest,
    )

    assert report["status"] == "pass"
    assert report["summary"]["failed"] == 0


def test_verify_container_release_accepts_readme_relative_paths(tmp_path):
    digest = "sha256:" + ("a" * 64)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("evidence").mkdir()
        result = runner.invoke(
            cli,
            [
                "supply-chain",
                "container-release",
                "--image",
                "ghcr.io/bamboogap/skills-orchestrator",
                "--tag",
                "v4.8.0",
                "--digest",
                digest,
                "--repository",
                "BambooGap/skills-orchestrator",
                "--commit",
                "local-fixture",
                "--workflow-run-url",
                "https://github.com/BambooGap/skills-orchestrator/actions/runs/0",
                "--sbom-output",
                "evidence/container-sbom.cdx.json",
                "--provenance-output",
                "evidence/container-provenance.json",
                "--no-dependencies",
                "--force",
            ],
        )
        assert result.exit_code == 0

        verify = runner.invoke(
            cli,
            [
                "supply-chain",
                "verify-container-release",
                "--provenance",
                "evidence/container-provenance.json",
                "--sbom",
                "evidence/container-sbom.cdx.json",
                "--image",
                "ghcr.io/bamboogap/skills-orchestrator",
                "--tag",
                "v4.8.0",
                "--digest",
                digest,
                "--format",
                "json",
            ],
        )

    assert verify.exit_code == 0
    payload = json.loads(verify.output)
    assert payload["status"] == "pass"
    assert payload["summary"] == {"passed": 8, "failed": 0}


def test_verify_container_release_reports_digest_and_sbom_mismatches(tmp_path):
    digest = "sha256:" + ("e" * 64)
    sbom_path = tmp_path / "container-sbom.cdx.json"
    provenance_path = tmp_path / "container-provenance.json"
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "supply-chain",
            "container-release",
            "--image",
            "ghcr.io/bamboogap/skills-orchestrator",
            "--tag",
            "v4.8.0",
            "--digest",
            digest,
            "--sbom-output",
            str(sbom_path),
            "--provenance-output",
            str(provenance_path),
            "--no-dependencies",
        ],
    )
    sbom_path.write_text("tampered\n", encoding="utf-8")

    report = verify_container_release(
        provenance_path=provenance_path,
        sbom_path=sbom_path,
        expected_digest="sha256:" + ("f" * 64),
    )

    failed = {check["id"] for check in report["checks"] if check["status"] == "fail"}
    assert report["status"] == "fail"
    assert {"expected-digest", "sbom-sha256"} <= failed


def test_verify_container_release_rejects_malformed_provenance_digest(tmp_path):
    digest = "sha256:" + ("0" * 64)
    sbom_path = tmp_path / "container-sbom.cdx.json"
    provenance_path = tmp_path / "container-provenance.json"
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "supply-chain",
            "container-release",
            "--image",
            "ghcr.io/bamboogap/skills-orchestrator",
            "--tag",
            "v4.8.0",
            "--digest",
            digest,
            "--sbom-output",
            str(sbom_path),
            "--provenance-output",
            str(provenance_path),
            "--no-dependencies",
        ],
    )
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["image"]["digest"] = "latest"
    provenance["image"]["reference"] = "ghcr.io/bamboogap/skills-orchestrator@latest"
    provenance["attestations"]["provenance_subject"]["subject_digest"] = "latest"
    provenance["attestations"]["sbom_subject"]["subject_digest"] = "latest"
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")

    report = verify_container_release(provenance_path=provenance_path, sbom_path=sbom_path)

    failed = {check["id"] for check in report["checks"] if check["status"] == "fail"}
    assert report["status"] == "fail"
    assert {"image-digest-format", "provenance-subject", "sbom-subject"} <= failed


def test_verify_container_release_cli_outputs_json(tmp_path):
    digest = "sha256:" + ("1" * 64)
    sbom_path = tmp_path / "container-sbom.cdx.json"
    provenance_path = tmp_path / "container-provenance.json"
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "supply-chain",
            "container-release",
            "--image",
            "ghcr.io/bamboogap/skills-orchestrator",
            "--tag",
            "v4.8.0",
            "--digest",
            digest,
            "--sbom-output",
            str(sbom_path),
            "--provenance-output",
            str(provenance_path),
            "--no-dependencies",
        ],
    )

    result = runner.invoke(
        cli,
        [
            "supply-chain",
            "verify-container-release",
            "--provenance",
            str(provenance_path),
            "--sbom",
            str(sbom_path),
            "--digest",
            digest,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "pass"
    report_path = tmp_path / "container-release-verification.json"
    report_path.write_text(result.output, encoding="utf-8")
    assert validate_document("container-release-verification", str(report_path)).valid is True
