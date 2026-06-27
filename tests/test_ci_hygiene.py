from pathlib import Path

from scripts.check_pip_constraints import find_unconstrained_installs


def test_pip_constraints_check_flags_unconstrained_install(tmp_path: Path):
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        """
name: example
steps:
  - run: python -m pip install pip-audit==2.10.1
""",
        encoding="utf-8",
    )

    issues = find_unconstrained_installs(workflow)

    assert len(issues) == 1
    assert "missing constraints.txt" in issues[0]


def test_pip_constraints_check_accepts_constraints_file(tmp_path: Path):
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        """
steps:
  - run: python -m pip install -c constraints.txt pip-audit==2.10.1
""",
        encoding="utf-8",
    )

    assert find_unconstrained_installs(workflow) == []


def test_pip_constraints_check_accepts_wheel_smoke_install(tmp_path: Path):
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        """
steps:
  - run: /tmp/smoke/bin/python -m pip install dist/*.whl
""",
        encoding="utf-8",
    )

    assert find_unconstrained_installs(workflow) == []


def test_pip_constraints_check_joins_backslash_continuations(tmp_path: Path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        """
RUN python -m pip install \\
    -c constraints.txt \\
    .
""",
        encoding="utf-8",
    )

    assert find_unconstrained_installs(dockerfile) == []
