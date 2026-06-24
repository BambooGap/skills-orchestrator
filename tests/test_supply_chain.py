import json

from click.testing import CliRunner

from skills_orchestrator.main import cli
from skills_orchestrator.schema_validation import validate_document
from skills_orchestrator.supply_chain import build_container_image_sbom


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
