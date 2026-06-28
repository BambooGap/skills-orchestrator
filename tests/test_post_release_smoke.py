import scripts.post_release_smoke as smoke
from scripts.post_release_smoke import (
    Check,
    build_report,
    fetch_json,
    ghcr_manifest_check,
    ghcr_signature_check,
    github_token_from_env,
    github_release_check,
    pypi_hash_locked_install_smoke,
    pypi_install_smoke,
    parse_imagetools_output,
    pypi_release_check,
    supports_optional_mcp_runtime,
    wheel_requirement_line,
)


def test_fetch_json_adds_github_token_headers(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, *, timeout):
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(smoke.urllib.request, "urlopen", fake_urlopen)

    assert fetch_json(
        "https://api.github.com/repos/example/project", timeout=12, token="token"
    ) == {"ok": True}
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["headers"]["X-github-api-version"] == "2022-11-28"
    assert captured["timeout"] == 12


def test_github_token_from_env_prefers_github_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "github-token")
    monkeypatch.setenv("GH_TOKEN", "gh-token")

    assert github_token_from_env() == "github-token"


def test_pypi_release_check_requires_wheel_and_sdist():
    checks = pypi_release_check(
        {
            "info": {"version": "4.7.8"},
            "releases": {
                "4.7.8": [
                    {"filename": "skills_orchestrator-4.7.8-py3-none-any.whl"},
                    {"filename": "skills_orchestrator-4.7.8.tar.gz"},
                ]
            },
        },
        package="skills-orchestrator",
        version="v4.7.8",
    )

    assert all(check.ok for check in checks)


def test_pypi_release_check_flags_missing_sdist():
    checks = pypi_release_check(
        {
            "info": {"version": "4.7.8"},
            "releases": {"4.7.8": [{"filename": "skills_orchestrator-4.7.8-py3-none-any.whl"}]},
        },
        package="skills-orchestrator",
        version="4.7.8",
    )

    failed = {check.name for check in checks if not check.ok}
    assert failed == {"pypi-sdist-present"}


def test_github_release_check_flags_draft_release():
    checks = github_release_check(
        {"tag_name": "v4.7.8", "draft": True, "prerelease": False},
        version="4.7.8",
    )

    failed = {check.name for check in checks if not check.ok}
    assert failed == {"github-release-not-draft"}


def test_parse_imagetools_output_extracts_digest_platforms_and_attestations():
    output = """
Name:      ghcr.io/example/project:v1.2.3
MediaType: application/vnd.oci.image.index.v1+json
Digest:    sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

Manifests:
  Name:        ghcr.io/example/project@sha256:bbbb
  Platform:    linux/amd64

  Name:        ghcr.io/example/project@sha256:cccc
  Platform:    linux/arm64

  Name:        ghcr.io/example/project@sha256:dddd
  Platform:    unknown/unknown
  Annotations:
    vnd.docker.reference.type:   attestation-manifest
"""

    digest, platforms, has_attestation = parse_imagetools_output(output)

    assert digest == "sha256:" + "a" * 64
    assert platforms == {"linux/amd64", "linux/arm64", "unknown/unknown"}
    assert has_attestation is True


def test_ghcr_manifest_check_flags_missing_required_platform():
    output = """
Digest:    sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  Platform:    linux/amd64
"""

    checks = ghcr_manifest_check(
        output,
        required_platforms={"linux/amd64", "linux/arm64"},
        require_attestations=False,
    )

    failed = {check.name for check in checks if not check.ok}
    assert failed == {"ghcr-required-platforms"}


def test_ghcr_signature_check_requires_cosign_cli(monkeypatch):
    monkeypatch.setattr(smoke.shutil, "which", lambda _name: None)

    checks = ghcr_signature_check(
        image="ghcr.io/example/project",
        digest="sha256:" + "a" * 64,
        repo="example/project",
        timeout=30,
    )

    assert checks == [Check("ghcr-cosign-cli", False, "cosign CLI is not available")]


def test_ghcr_signature_check_verifies_digest_identity(monkeypatch):
    captured = {}
    digest = "sha256:" + "a" * 64

    monkeypatch.setattr(smoke.shutil, "which", lambda _name: "/usr/local/bin/cosign")

    def fake_run_command(command, *, cwd=None, timeout=120):
        del cwd
        captured["command"] = command
        captured["timeout"] = timeout
        return smoke.subprocess.CompletedProcess(command, 0, "Verified OK\n", "")

    monkeypatch.setattr(smoke, "run_command", fake_run_command)

    checks = ghcr_signature_check(
        image="ghcr.io/example/project",
        digest=digest,
        repo="example/project",
        timeout=42,
    )

    assert checks == [Check("ghcr-cosign-signature", True, "cosign signature verified")]
    assert captured["timeout"] == 42
    assert captured["command"] == [
        "cosign",
        "verify",
        "--certificate-identity-regexp",
        r"^https://github\.com/example/project/\.github/workflows/ghcr\.yml@refs/(tags|heads)/.+$",
        "--certificate-oidc-issuer",
        "https://token.actions.githubusercontent.com",
        f"ghcr.io/example/project@{digest}",
    ]


def test_main_retries_until_checks_pass(monkeypatch):
    attempts = []

    def fake_collect_checks(_args):
        attempts.append(1)
        return [Check("eventual-readiness", len(attempts) == 2, "ready")]

    monkeypatch.setattr(smoke, "collect_checks", fake_collect_checks)
    monkeypatch.setattr(smoke.time, "sleep", lambda _seconds: None)

    exit_code = smoke.main(
        [
            "--version",
            "v1.2.3",
            "--skip-github",
            "--skip-pypi",
            "--skip-ghcr",
            "--retries",
            "2",
            "--retry-delay",
            "0",
        ]
    )

    assert exit_code == 0
    assert len(attempts) == 2


def test_build_report_has_stable_schema_version():
    report = build_report([Check("github-release-tag", True, "ready")])

    assert report == {
        "schema_version": "skills-orchestrator.post-release-smoke.v1",
        "status": "pass",
        "summary": {"passed": 1, "failed": 0},
        "checks": [{"name": "github-release-tag", "ok": True, "message": "ready"}],
    }


def test_supports_optional_mcp_runtime_starts_at_4_8_0():
    assert supports_optional_mcp_runtime("v4.8.0") is True
    assert supports_optional_mcp_runtime("4.8.1") is True
    assert supports_optional_mcp_runtime("4.7.11") is False
    assert supports_optional_mcp_runtime("not-a-version") is False


def test_wheel_requirement_line_generates_pip_hash(tmp_path):
    wheel = tmp_path / "skills_orchestrator-4.8.20-py3-none-any.whl"
    wheel.write_bytes(b"fake wheel bytes")

    line = wheel_requirement_line(wheel)

    assert line.startswith("skills-orchestrator==4.8.20 --hash=sha256:")
    assert len(line.rsplit(":", 1)[1]) == 64


def test_pypi_install_smoke_checks_default_mcp_extra_hint(monkeypatch):
    def fake_run_command(command, *, cwd=None, timeout=120):
        del cwd, timeout
        if len(command) >= 4 and command[1:3] == ["-m", "venv"]:
            return smoke.subprocess.CompletedProcess(command, 0, "", "")
        if command[1:4] == ["-m", "pip", "install"]:
            return smoke.subprocess.CompletedProcess(command, 0, "installed\n", "")
        if command[1:4] == ["-m", "pip", "check"]:
            return smoke.subprocess.CompletedProcess(
                command, 0, "No broken requirements found.\n", ""
            )
        if command[1] == "-c":
            return smoke.subprocess.CompletedProcess(command, 0, "", "")
        if command[-1] == "--version":
            return smoke.subprocess.CompletedProcess(
                command, 0, "skills-orchestrator, version 4.8.1\n", ""
            )
        if command[1:4] == ["mcp-test", "list_skills", "{}"]:
            return smoke.subprocess.CompletedProcess(
                command,
                1,
                "",
                '✗ 请运行: python3.12 -m pip install "skills-orchestrator[mcp]"\n',
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(smoke, "run_command", fake_run_command)

    checks = pypi_install_smoke(
        package="skills-orchestrator",
        version="4.8.1",
        python="python3.12",
        check_new_user_path=False,
        timeout=30,
    )

    by_name = {check.name: check for check in checks}
    assert by_name["pypi-default-without-mcp"].ok is True
    assert by_name["pypi-mcp-extra-hint"].ok is True


def test_pypi_hash_locked_install_smoke_builds_local_wheelhouse(monkeypatch):
    install_commands = []

    def fake_run_command(command, *, cwd=None, timeout=120):
        del cwd, timeout
        if command[1:4] == ["-m", "pip", "download"]:
            wheelhouse = command[command.index("--dest") + 1]
            (smoke.Path(wheelhouse) / "skills_orchestrator-4.8.20-py3-none-any.whl").write_bytes(
                b"skillops"
            )
            (smoke.Path(wheelhouse) / "click-8.4.2-py3-none-any.whl").write_bytes(b"click")
            return smoke.subprocess.CompletedProcess(command, 0, "downloaded\n", "")
        if len(command) >= 4 and command[1:3] == ["-m", "venv"]:
            return smoke.subprocess.CompletedProcess(command, 0, "", "")
        if command[1:4] == ["-m", "pip", "install"]:
            install_commands.append(command)
            assert "--require-hashes" in command
            assert "--no-index" in command
            lock_file = smoke.Path(command[command.index("-r") + 1])
            lock_text = lock_file.read_text(encoding="utf-8")
            assert "skills-orchestrator==4.8.20 --hash=sha256:" in lock_text
            assert "click==8.4.2 --hash=sha256:" in lock_text
            return smoke.subprocess.CompletedProcess(command, 0, "installed\n", "")
        if command[1:4] == ["-m", "pip", "check"]:
            return smoke.subprocess.CompletedProcess(
                command, 0, "No broken requirements found.\n", ""
            )
        if command[-1] == "--version":
            return smoke.subprocess.CompletedProcess(
                command, 0, "skills-orchestrator, version 4.8.20\n", ""
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(smoke, "run_command", fake_run_command)

    checks = pypi_hash_locked_install_smoke(
        package="skills-orchestrator",
        version="4.8.20",
        python="python3.12",
        timeout=30,
    )

    assert install_commands
    by_name = {check.name: check for check in checks}
    assert by_name["pypi-hash-lock-download"].ok is True
    assert by_name["pypi-hash-lock-file"].ok is True
    assert by_name["pypi-hash-lock-install"].ok is True
    assert by_name["pypi-hash-lock-cli-version"].ok is True
    assert by_name["pypi-hash-lock-pip-check"].ok is True


def test_pypi_install_smoke_does_not_require_mcp_extra_hint_for_older_releases(monkeypatch):
    def fake_run_command(command, *, cwd=None, timeout=120):
        del cwd, timeout
        if len(command) >= 4 and command[1:3] == ["-m", "venv"]:
            return smoke.subprocess.CompletedProcess(command, 0, "", "")
        if command[1:4] == ["-m", "pip", "install"]:
            return smoke.subprocess.CompletedProcess(command, 0, "installed\n", "")
        if command[1:4] == ["-m", "pip", "check"]:
            return smoke.subprocess.CompletedProcess(
                command, 0, "No broken requirements found.\n", ""
            )
        if command[-1] == "--version":
            return smoke.subprocess.CompletedProcess(
                command, 0, "skills-orchestrator, version 4.7.11\n", ""
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(smoke, "run_command", fake_run_command)

    checks = pypi_install_smoke(
        package="skills-orchestrator",
        version="4.7.11",
        python="python3.12",
        check_new_user_path=False,
        timeout=30,
    )

    check_names = {check.name for check in checks}
    assert "pypi-default-without-mcp" not in check_names
    assert "pypi-mcp-extra-hint" not in check_names
