from pathlib import Path

from skills_orchestrator.schema_validation import validate_document


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "agent-handoff"


def test_agent_handoff_example_validates():
    result = validate_document("agent-handoff", str(EXAMPLE / "release-review-handoff.json"))

    assert result.valid is True


def test_agent_handoff_rejects_privileged_worker_without_approval():
    result = validate_document("agent-handoff", str(EXAMPLE / "invalid-privileged-worker.json"))

    assert result.valid is False
    paths = {error.path for error in result.errors}
    assert "$.workers[0].requires_human_approval" in paths


def test_agent_handoff_rejects_privileged_worker_without_human_review_gate():
    result = validate_document(
        "agent-handoff",
        str(EXAMPLE / "invalid-privileged-without-human-review.json"),
    )

    assert result.valid is False
    paths = {error.path for error in result.errors}
    assert "$.evaluation.gates" in paths
    assert any("does not contain" in error.message for error in result.errors)


def test_agent_handoff_rejects_production_handoff_without_explainability_evidence():
    result = validate_document("agent-handoff", str(EXAMPLE / "invalid-production-evidence.json"))

    assert result.valid is False
    paths = {error.path for error in result.errors}
    assert "$.evidence.required_artifacts" in paths
    assert any("does not contain" in error.message for error in result.errors)
