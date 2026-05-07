"""Release/version consistency checks."""

from __future__ import annotations

import tomllib
from pathlib import Path

import skills_orchestrator


def test_package_version_matches_pyproject():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert data["project"]["version"] == skills_orchestrator.__version__
