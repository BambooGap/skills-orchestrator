"""Adoption examples should stay copyable and version-current."""

from __future__ import annotations

from pathlib import Path

import pytest

from skills_orchestrator import __version__
from skills_orchestrator.checker import run_check


ROOT = Path(__file__).resolve().parents[1]
ADOPTION_DIR = ROOT / "examples" / "adoption-repos"
ADOPTION_CONFIGS = sorted(ADOPTION_DIR.glob("*/config/skills.yaml"))


def _adoption_root(config_path: Path) -> Path:
    return config_path.parents[1]


def test_adoption_examples_exist():
    assert {path.parents[1].name for path in ADOPTION_CONFIGS} == {
        "healthchecks",
        "umami",
        "woodpecker",
    }


@pytest.mark.parametrize("config_path", ADOPTION_CONFIGS, ids=lambda path: path.parents[1].name)
def test_adoption_example_passes_team_standard(config_path: Path):
    report = run_check(str(config_path), policy_packs=["builtin/team-standard"])

    assert report.diagnostics == []


@pytest.mark.parametrize("config_path", ADOPTION_CONFIGS, ids=lambda path: path.parents[1].name)
def test_adoption_workflow_uses_current_release_tag(config_path: Path):
    workflow_path = _adoption_root(config_path) / ".github" / "workflows" / "skillops.yml"

    assert f"BambooGap/skills-orchestrator@v{__version__}" in workflow_path.read_text(
        encoding="utf-8"
    )
