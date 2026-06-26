from pathlib import Path

import pytest

from skills_orchestrator.schema_validation import validate_document


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_CONSUMER = ROOT / "examples" / "external-consumer"


@pytest.mark.parametrize(
    ("kind", "filename"),
    [
        ("hosted-registry-ingest", "hosted-registry-ingest.json"),
        ("github-app-installation", "github-app-installation.json"),
        ("multi-repo-artifacts", "multi-repo-artifacts.json"),
    ],
)
def test_external_consumer_examples_validate(kind: str, filename: str):
    result = validate_document(kind, str(EXTERNAL_CONSUMER / filename))

    assert result.valid is True


def test_external_consumer_readme_keeps_core_boundary():
    readme = (EXTERNAL_CONSUMER / "README.md").read_text(encoding="utf-8")

    assert "no database" in readme
    assert "no server" in readme
    assert "should not parse skill" in readme
    assert "Markdown directly" in readme
    assert "second\npolicy engine" in readme
