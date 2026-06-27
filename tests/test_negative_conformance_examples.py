import json
from pathlib import Path

import pytest

from skills_orchestrator.checker import run_check


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "examples" / "negative-conformance"


def _cases():
    payload = json.loads((FIXTURE_ROOT / "cases.json").read_text(encoding="utf-8"))
    return payload["cases"]


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
def test_negative_conformance_fixture_reports_expected_rules(case):
    config = FIXTURE_ROOT / case["config"]

    report = run_check(str(config), policy_packs=case["policy_packs"])

    actual_rules = {diagnostic.rule_id for diagnostic in report.diagnostics}
    assert set(case["expected_rules"]) <= actual_rules


def test_negative_conformance_fixture_index_is_complete():
    cases = _cases()

    assert len(cases) == 7
    assert {case["id"] for case in cases} == {
        "duplicate-id",
        "expired-review-window",
        "external-trust",
        "invalid-lifecycle-required-approvers",
        "invalid-load-policy",
        "invalid-review-window",
        "missing-governance",
    }
    for case in cases:
        assert (FIXTURE_ROOT / case["config"]).exists()
        assert case["expected_rules"]
