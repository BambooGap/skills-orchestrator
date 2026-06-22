import json
from pathlib import Path

from skills_orchestrator.checker import run_check
from skills_orchestrator.diagnostic import DiagnosticSeverity
from skills_orchestrator.formatters import format_diagnostics_json, format_diagnostics_sarif


def _write_config(tmp_path, skills_dir):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "skills.yaml"
    config_file.write_text(
        f"""
version: "2.0"
skill_dirs:
  - {skills_dir.resolve()}
zones:
  - id: default
    name: 默认区
    load_policy: free
    rules: []
""",
        encoding="utf-8",
    )
    return config_file


def test_run_check_reports_metadata_and_asymmetric_conflict(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "a.md").write_text(
        "---\nid: skill-a\nname: Skill A\nsummary: A\nconflict_with: [skill-b]\n---\n# A\n",
        encoding="utf-8",
    )
    (skills_dir / "b.md").write_text(
        "---\nid: skill-b\nname: Skill B\n---\n# B\n",
        encoding="utf-8",
    )
    config = _write_config(tmp_path, skills_dir)

    report = run_check(str(config))

    rule_ids = {diagnostic.rule_id for diagnostic in report.diagnostics}
    assert "SO001" in rule_ids
    assert "SO004" in rule_ids
    assert all(d.severity != DiagnosticSeverity.ERROR for d in report.diagnostics)


def test_run_check_reports_duplicate_skill_id_as_warning(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    for filename in ("first.md", "second.md"):
        (skills_dir / filename).write_text(
            "---\nid: duplicate\nname: Duplicate\nsummary: duplicate\n---\n",
            encoding="utf-8",
        )
    config = _write_config(tmp_path, skills_dir)

    report = run_check(str(config))

    duplicate = [diagnostic for diagnostic in report.diagnostics if diagnostic.rule_id == "SO002"]
    assert len(duplicate) == 1
    assert duplicate[0].severity == DiagnosticSeverity.WARNING
    assert not Path(duplicate[0].metadata["first_path"]).is_absolute()
    assert not Path(duplicate[0].metadata["duplicate_path"]).is_absolute()
    assert str(tmp_path) not in duplicate[0].message


def test_formatters_emit_json_and_sarif(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "missing.md").write_text(
        "---\nid: missing\nname: Missing\n---\n# Missing\n",
        encoding="utf-8",
    )
    config = _write_config(tmp_path, skills_dir)
    report = run_check(str(config))

    json_payload = json.loads(format_diagnostics_json(report))
    assert json_payload["tool"]["name"] == "skills-orchestrator"
    assert json_payload["diagnostics"][0]["rule_id"] == "SO001"
    assert json_payload["policy_trace"][0]["rule_id"] == "SO001"
    assert json_payload["policy_trace"][0]["outcome"] == "fail"

    sarif_payload = json.loads(format_diagnostics_sarif(report))
    assert sarif_payload["version"] == "2.1.0"
    assert sarif_payload["runs"][0]["tool"]["driver"]["name"] == "skills-orchestrator"
    assert sarif_payload["runs"][0]["results"][0]["ruleId"] == "SO001"


def test_policy_trace_records_passed_policy_rules(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "team.md").write_text(
        "---\n"
        "id: team\n"
        "name: Team\n"
        "summary: Team skill\n"
        "owner: platform-team\n"
        "source: internal://team\n"
        "version: 1.0.0\n"
        "lifecycle: active\n"
        "---\n"
        "# Team\n",
        encoding="utf-8",
    )
    config = _write_config(tmp_path, skills_dir)

    report = run_check(str(config), policy_packs=["builtin/team-standard"])
    payload = json.loads(format_diagnostics_json(report))
    passed = {
        item["rule_id"]: item
        for item in payload["policy_trace"]
        if item["outcome"] == "pass" and item["policy_pack"] == "builtin/team-standard"
    }

    assert not report.diagnostics
    assert {"SO008", "SO009", "SO010", "SO011", "SO012"}.issubset(passed)
    assert passed["SO008"]["scope"] == "policy_pack"
