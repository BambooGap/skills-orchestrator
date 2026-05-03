"""Enforcer - Zone 探测 + 运行时强制执行"""

from fnmatch import fnmatch
from pathlib import Path

from skills_orchestrator.models import Zone, Config, Manifest, LoadPlan


class Enforcer:
    """运行时执行器"""

    def __init__(self, config: Config, manifest: Manifest):
        self.config = config
        self.manifest = manifest

    def detect_zone(self, workdir: str) -> Zone:
        """按 priority 从高到低匹配 Zone 规则"""
        workdir_path = Path(workdir).resolve()

        # 按 priority 从高到低排序
        sorted_zones = sorted(self.config.zones, key=lambda z: -z.priority)

        for zone in sorted_zones:
            for rule in zone.rules:
                # glob 路径匹配
                if rule.pattern and fnmatch(str(workdir_path), rule.pattern):
                    return zone

                # git config 匹配
                if rule.git_contains and self._git_match(workdir_path, rule):
                    return zone

        # 无匹配，回退 default zone
        return self.config.default_zone or Zone(
            id="default", name="默认区", load_policy="free", priority=0
        )

    def _git_match(self, workdir: Path, rule) -> bool:
        """检查 git remote URL 是否包含指定字符串。

        git_contains 设计意图是匹配 git remote 中的域名/组织，
        如 "company.com" 匹配 remote "git@company.com:team/repo.git"。
        如果不是 git 仓库，回退到检查 marker 文件是否存在。
        """
        target = rule.git_contains
        if not target:
            return False

        # 找 git 仓库根目录
        try:
            import subprocess

            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(workdir),
                env={"PATH": "/usr/bin:/usr/local/bin"},
            )
            if result.returncode != 0:
                # 不是 git 仓库，回退到 marker 文件
                return (workdir / target).exists()

            git_root = result.stdout.strip()

            # 获取 remote URL 列表
            result = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=git_root,
                env={"PATH": "/usr/bin:/usr/local/bin"},
            )
            if result.returncode == 0 and target in result.stdout:
                return True

            # 也检查 .gitconfig 中的用户/组织信息
            result = subprocess.run(
                ["git", "config", "--list", "--local"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=git_root,
                env={"PATH": "/usr/bin:/usr/local/bin"},
            )
            if result.returncode == 0 and target in result.stdout:
                return True

        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 回退：检查 marker 文件
        return (workdir / target).exists()

    def apply(self, workdir: str) -> LoadPlan:
        """应用 LoadPlan"""
        zone = self.detect_zone(workdir)

        return LoadPlan(
            forced=self.manifest.forced_content,
            passive_index=self.manifest.passive_index,
            blocked=self.manifest.blocked_list,
            active_zone=zone.id,
        )
