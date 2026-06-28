from pathlib import Path

from skills_orchestrator.schema_validation import validate_document


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "agent-runtime-image"


def test_agent_runtime_image_example_validates():
    result = validate_document("agent-runtime-image", str(EXAMPLE / "codex-worker-image.json"))

    assert result.valid is True


def test_agent_runtime_image_negative_fixture_rejects_floating_and_unapproved_privilege():
    result = validate_document("agent-runtime-image", str(EXAMPLE / "invalid-floating-tag.json"))

    assert result.valid is False
    messages = "\n".join(error.message for error in result.errors)
    assert "'latest' does not match" in messages
    paths = {error.path for error in result.errors}
    assert "$.permission_boundary.human_approval.required_for" in paths
    assert (
        sum(
            1
            for error in result.errors
            if error.path == "$.permission_boundary.human_approval.required_for"
        )
        == 3
    )
