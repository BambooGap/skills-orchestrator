"""端到端集成测试 — 验证 Pipeline 全链路：YAML → Loader → Engine → Store → MCP Tools → CLI"""

import os
import re


from skills_orchestrator.mcp.registry import SkillRegistry
from skills_orchestrator.mcp.tools import ToolExecutor
from skills_orchestrator.pipeline.store import RunStateStore


# ─────────────────── helpers ───────────────────

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "skills.yaml")
PIPELINES_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "pipelines")


def _registry():
    return SkillRegistry(os.path.normpath(CONFIG_PATH))


def _pipelines_dir():
    return os.path.normpath(PIPELINES_DIR)


def _executor(store_dir=None):
    reg = _registry()
    ex = ToolExecutor(reg, pipelines_dir=_pipelines_dir())
    if store_dir:
        ex._store = RunStateStore(base_dir=store_dir)
    return ex


# ═══════════════════════════════════════════════════════════
# E2E: YAML 加载 → Engine 启动 → Store 持久化 → 恢复
# ═══════════════════════════════════════════════════════════


class TestE2EFullDevPipeline:
    """完整 full-dev pipeline 端到端：启动→逐步推进→持久化→中断恢复→完成"""

    def test_full_lifecycle(self, tmp_path):
        """5步完整走完 + 持久化 + 中断恢复"""
        store_dir = str(tmp_path / "runs")
        executor = _executor(store_dir)

        # 1. 启动 full-dev
        result = executor.execute("pipeline_start", {"pipeline_id": "full-dev"})
        text = result[0].text
        assert "已启动" in text
        assert "brainstorm" in text
        match = re.search(r"Run ID: (\w+)", text)
        run_id = match.group(1)

        # 2. 推进 brainstorm → plan (门禁: brainstorm_output)
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["brainstorm_output"],
                "context_updates": {"brainstorm_output": "功能构想和关键决策"},
            },
        )
        assert "plan" in result[0].text

        # 3. 检查状态
        result = executor.execute(
            "pipeline_status",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
            },
        )
        assert "plan" in result[0].text
        assert "running" in result[0].text.lower()

        # 4. 中断恢复 — 新建 executor 实例（模拟进程重启）
        executor2 = _executor(store_dir)
        result = executor2.execute(
            "pipeline_resume",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
            },
        )
        assert "已恢复" in result[0].text
        assert "plan" in result[0].text

        # 5. 推进 plan → develop（门禁: implementation_plan, min_length 500）
        result = executor2.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["implementation_plan"],
                "context_updates": {"implementation_plan": "X" * 600},
            },
        )
        text = result[0].text
        assert "develop" in text or "review" in text or "已完成" in text

        # 6. 推进 develop → review（门禁: code_changes）
        result = executor2.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["code_changes"],
                "context_updates": {"code_changes": "changed"},
            },
        )

        # 7. 推进 review → finish（门禁: review_feedback）
        result = executor2.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["review_feedback"],
                "context_updates": {"review_feedback": "LGTM"},
            },
        )

        # 8. 推进 finish → 完成（门禁: merge_confirmation）
        result = executor2.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["merge_confirmation"],
                "context_updates": {"merge_confirmation": "merged to main"},
            },
        )
        text = result[0].text
        assert "已完成" in text or "completed" in text.lower()

        # 9. 最终状态检查
        result = executor2.execute(
            "pipeline_status",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
            },
        )
        assert "completed" in result[0].text.lower()

    def test_skip_logic(self, tmp_path):
        """scope_is_trivial 跳过 brainstorm"""
        store_dir = str(tmp_path / "runs")
        executor = _executor(store_dir)

        result = executor.execute(
            "pipeline_start",
            {
                "pipeline_id": "full-dev",
                "context": {"scope_is_trivial": True},
            },
        )
        text = result[0].text
        # brainstorm 被跳过，应直接到 plan
        assert "plan" in text


class TestE2EQuickFixPipeline:
    """quick-fix pipeline 端到端"""

    def test_quick_fix_lifecycle(self, tmp_path):
        store_dir = str(tmp_path / "runs")
        executor = _executor(store_dir)

        # 启动
        result = executor.execute("pipeline_start", {"pipeline_id": "quick-fix"})
        text = result[0].text
        assert "已启动" in text
        match = re.search(r"Run ID: (\w+)", text)
        run_id = match.group(1)

        # 推进 debug → fix（门禁: root_cause）
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "quick-fix",
                "artifacts": ["root_cause"],
                "context_updates": {"root_cause": "null pointer in line 42"},
            },
        )
        assert "fix" in result[0].text

        # 推进 fix → commit（门禁: code_changes）
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "quick-fix",
                "artifacts": ["code_changes"],
                "context_updates": {"code_changes": "added null check"},
            },
        )
        assert "commit" in result[0].text or "已完成" in result[0].text

        # 推进 commit → 完成（门禁: commit_sha）
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "quick-fix",
                "artifacts": ["commit_sha"],
                "context_updates": {"commit_sha": "abc123"},
            },
        )
        assert "已完成" in result[0].text or "completed" in result[0].text.lower()


class TestE2EReviewOnlyPipeline:
    """review-only pipeline 端到端"""

    def test_review_only_lifecycle(self, tmp_path):
        store_dir = str(tmp_path / "runs")
        executor = _executor(store_dir)

        result = executor.execute("pipeline_start", {"pipeline_id": "review-only"})
        text = result[0].text
        match = re.search(r"Run ID: (\w+)", text)
        run_id = match.group(1)

        # 推进 review → finish（门禁: review_feedback）
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "review-only",
                "artifacts": ["review_feedback"],
                "context_updates": {"review_feedback": "Needs work"},
            },
        )
        assert "finish" in result[0].text.lower()

        # 推进 finish → 完成（门禁: merge_confirmation）
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "review-only",
                "artifacts": ["merge_confirmation"],
                "context_updates": {"merge_confirmation": "merged"},
            },
        )
        assert "已完成" in result[0].text or "completed" in result[0].text.lower()


class TestE2EAbortAndResume:
    """中断-恢复场景"""

    def test_abort_and_resume(self, tmp_path):
        store_dir = str(tmp_path / "runs")
        executor = _executor(store_dir)

        # 启动
        result = executor.execute("pipeline_start", {"pipeline_id": "full-dev"})
        match = re.search(r"Run ID: (\w+)", result[0].text)
        run_id = match.group(1)

        # 推进一步（门禁: brainstorm_output）
        executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["brainstorm_output"],
                "context_updates": {"brainstorm_output": "some output"},
            },
        )

        # 模拟新进程恢复
        executor2 = _executor(store_dir)
        result = executor2.execute(
            "pipeline_resume",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
            },
        )
        assert "已恢复" in result[0].text

    def test_list_runs(self, tmp_path):
        """多个 run 并存，list 正确"""
        store_dir = str(tmp_path / "runs")
        executor = _executor(store_dir)

        # 启动两个 pipeline
        executor.execute("pipeline_start", {"pipeline_id": "full-dev"})
        executor.execute("pipeline_start", {"pipeline_id": "quick-fix"})

        # 查看 status — 不带参数应列出所有
        result = executor.execute("pipeline_status", {})
        text = result[0].text
        # 至少应提到一个 pipeline
        assert "full-dev" in text or "quick-fix" in text


class TestE2ECLIIntegration:
    """CLI 命令端到端 — 通过 subprocess 调用"""

    def test_pipeline_list(self):
        import subprocess

        result = subprocess.run(
            ["python", "-m", "skills_orchestrator.main", "pipeline", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.path.dirname(__file__),
        )
        assert result.returncode == 0
        assert "full-dev" in result.stdout
        assert "quick-fix" in result.stdout
        assert "review-only" in result.stdout

    def test_pipeline_start_and_status(self):
        import subprocess

        cwd = os.path.join(os.path.dirname(__file__), "..")
        result = subprocess.run(
            [
                "python",
                "-m",
                "skills_orchestrator.main",
                "pipeline",
                "start",
                "quick-fix",
                "--config",
                "config/skills.yaml",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd,
        )
        assert result.returncode == 0
        assert "已启动" in result.stdout
        match = re.search(r"Run ID: (\w+)", result.stdout)
        assert match
        run_id = match.group(1)

        # 检查 status
        result2 = subprocess.run(
            [
                "python",
                "-m",
                "skills_orchestrator.main",
                "pipeline",
                "status",
                "--run-id",
                run_id,
                "--pipeline-id",
                "quick-fix",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd,
        )
        assert result2.returncode == 0
        assert run_id in result2.stdout
