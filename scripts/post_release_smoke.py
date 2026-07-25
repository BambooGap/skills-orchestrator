#!/usr/bin/env python3
"""Post-release smoke checks for GitHub, PyPI, and GHCR artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DIGEST_RE = re.compile(r"^Digest:\s+(sha256:[0-9a-f]{64})$", re.MULTILINE)
PLATFORM_RE = re.compile(r"^\s*Platform:\s+(\S+)\s*$", re.MULTILINE)
ATTESTATION_RE = re.compile(r"vnd\.docker\.reference\.type:\s+attestation-manifest")
DEFAULT_TIMEOUT_SECONDS = 60
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "message": self.message}


def normalize_version(version: str) -> str:
    return version[1:] if version.startswith("v") else version


def tag_for_version(version: str) -> str:
    normalized = normalize_version(version)
    return f"v{normalized}"


def fetch_json(url: str, *, timeout: float, token: str | None = None) -> Any:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def github_token_from_env() -> str | None:
    """Return the GitHub API token exposed by local or GitHub Actions environments."""
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def github_release_check(release: dict[str, Any], *, version: str) -> list[Check]:
    expected_tag = tag_for_version(version)
    checks = [
        Check(
            "github-release-tag",
            release.get("tag_name") == expected_tag,
            f"tag={release.get('tag_name')!r}, expected={expected_tag!r}",
        ),
        Check("github-release-not-draft", not bool(release.get("draft")), "release is not draft"),
        Check(
            "github-release-not-prerelease",
            not bool(release.get("prerelease")),
            "release is not prerelease",
        ),
    ]
    return checks


def pypi_release_check(project: dict[str, Any], *, package: str, version: str) -> list[Check]:
    normalized = normalize_version(version)
    releases = project.get("releases", {})
    files = releases.get(normalized, [])
    file_names = {entry.get("filename", "") for entry in files}
    has_wheel = any(name.endswith(".whl") for name in file_names)
    has_sdist = any(name.endswith(".tar.gz") for name in file_names)
    checks = [
        Check(
            "pypi-latest-version",
            project.get("info", {}).get("version") == normalized,
            f"latest={project.get('info', {}).get('version')!r}, expected={normalized!r}",
        ),
        Check(
            "pypi-release-present",
            normalized in releases,
            f"{package}=={normalized} is present in PyPI JSON",
        ),
        Check("pypi-wheel-present", has_wheel, f"files={sorted(file_names)}"),
        Check("pypi-sdist-present", has_sdist, f"files={sorted(file_names)}"),
    ]
    return checks


def parse_imagetools_output(output: str) -> tuple[str | None, set[str], bool]:
    digest_match = DIGEST_RE.search(output)
    digest = digest_match.group(1) if digest_match else None
    platforms = set(PLATFORM_RE.findall(output))
    has_attestation = bool(ATTESTATION_RE.search(output))
    return digest, platforms, has_attestation


def ghcr_manifest_check(
    output: str,
    *,
    required_platforms: set[str],
    require_attestations: bool,
) -> list[Check]:
    digest, platforms, has_attestation = parse_imagetools_output(output)
    missing_platforms = sorted(required_platforms - platforms)
    checks = [
        Check("ghcr-index-digest", digest is not None, f"digest={digest!r}"),
        Check(
            "ghcr-required-platforms",
            not missing_platforms,
            f"platforms={sorted(platforms)}, missing={missing_platforms}",
        ),
    ]
    if require_attestations:
        checks.append(
            Check(
                "ghcr-attestation-manifest",
                has_attestation,
                "attestation manifest is present in image index",
            )
        )
    return checks


def ghcr_signature_check(
    *,
    image: str,
    digest: str,
    repo: str,
    timeout: float,
) -> list[Check]:
    """Verify a GHCR image digest has a keyless cosign signature from this repo."""
    if not shutil.which("cosign"):
        return [Check("ghcr-cosign-cli", False, "cosign CLI is not available")]

    image_ref = f"{image}@{digest}"
    identity_regexp = (
        rf"^https://github\.com/{re.escape(repo)}/\.github/workflows/ghcr\.yml@"
        r"refs/(tags|heads)/.+$"
    )
    try:
        cp = run_command(
            [
                "cosign",
                "verify",
                "--certificate-identity-regexp",
                identity_regexp,
                "--certificate-oidc-issuer",
                "https://token.actions.githubusercontent.com",
                image_ref,
            ],
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return [Check("ghcr-cosign-signature", False, f"timed out after {timeout:.0f}s")]

    output = (cp.stdout or cp.stderr).strip()
    message = "cosign signature verified" if cp.returncode == 0 else output
    return [Check("ghcr-cosign-signature", cp.returncode == 0, message)]


def _contains_text(value: Any, needle: str) -> bool:
    """Return whether nested JSON-like data contains a case-insensitive text value."""
    if isinstance(value, str):
        return needle.lower() in value.lower()
    if isinstance(value, dict):
        return any(_contains_text(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, needle) for item in value)
    return False


def _cyclonedx_attestation_has_syft_tool(item: dict[str, Any]) -> bool:
    statement = (item.get("verificationResult") or {}).get("statement") or {}
    predicate = statement.get("predicate") or {}
    metadata = predicate.get("metadata") or {}
    tools = metadata.get("tools")
    return _contains_text(tools, "syft") or _contains_text(tools, "anchore")


def ghcr_os_sbom_attestation_check(
    *,
    image: str,
    digest: str,
    repo: str,
    version: str,
    timeout: float,
) -> list[Check]:
    """Verify the release digest has a CycloneDX attestation generated by Syft/Anchore."""
    if not shutil.which("gh"):
        return [Check("ghcr-os-sbom-attestation", False, "gh CLI is not available")]

    image_ref = f"oci://{image}@{digest}"
    tag = tag_for_version(version)
    try:
        cp = run_command(
            [
                "gh",
                "attestation",
                "verify",
                image_ref,
                "--repo",
                repo,
                "--signer-workflow",
                f"{repo}/.github/workflows/ghcr.yml",
                "--source-ref",
                f"refs/tags/{tag}",
                "--bundle-from-oci",
                "--predicate-type",
                "https://cyclonedx.org/bom",
                "--format",
                "json",
            ],
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return [Check("ghcr-os-sbom-attestation", False, f"timed out after {timeout:.0f}s")]

    if cp.returncode != 0:
        return [Check("ghcr-os-sbom-attestation", False, (cp.stderr or cp.stdout).strip())]
    try:
        attestations = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        return [Check("ghcr-os-sbom-attestation", False, f"invalid gh JSON output: {exc}")]

    has_syft = any(_cyclonedx_attestation_has_syft_tool(item) for item in attestations)
    return [
        Check(
            "ghcr-os-sbom-attestation",
            has_syft,
            f"found {len(attestations)} CycloneDX attestations; syft={has_syft}",
        )
    ]


def slsa_readiness_report_check(
    *,
    version: str,
    repo: str,
    image: str,
    digest: str,
) -> list[Check]:
    """Generate and schema-validate the non-certifying SLSA readiness report."""
    try:
        from skills_orchestrator.schema_validation import validate_document
        from skills_orchestrator.supply_chain import (
            build_slsa_readiness,
            format_slsa_readiness_json,
        )
    except Exception as exc:
        return [Check("slsa-readiness-report", False, f"could not import SkillOps CLI: {exc}")]

    try:
        report = build_slsa_readiness(
            release_version=version,
            repository=repo,
            image=image,
            digest=digest,
        )
        with tempfile.TemporaryDirectory(prefix="skillops-slsa-readiness-") as temp_dir:
            report_path = Path(temp_dir) / "slsa-readiness.json"
            report_path.write_text(format_slsa_readiness_json(report), encoding="utf-8")
            validation = validate_document("slsa-readiness", str(report_path))
    except Exception as exc:
        return [Check("slsa-readiness-report", False, str(exc))]

    if not validation.valid:
        messages = "; ".join(error.message for error in validation.errors[:3])
        return [Check("slsa-readiness-report", False, messages)]

    formal_claim = report.get("summary", {}).get("formal_claim")
    return [
        Check(
            "slsa-readiness-report",
            formal_claim is False,
            "schema valid; formal_claim=false"
            if formal_claim is False
            else f"formal_claim={formal_claim!r}",
        )
    ]


def run_command(
    command: list[str], *, cwd: Path | None = None, timeout: float = 120
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def wheel_requirement_line(path: Path) -> str:
    """Return a hash-locked requirement line for a downloaded wheel file."""
    parts = path.name.split("-")
    if len(parts) < 5 or not path.name.endswith(".whl"):
        raise ValueError(f"not a wheel filename: {path.name}")
    name = parts[0].replace("_", "-")
    version = parts[1]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"{name}=={version} --hash=sha256:{digest}"


def supports_optional_mcp_runtime(version: str) -> bool:
    """Return whether the release should keep MCP runtime out of the default install."""
    normalized = normalize_version(version)
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", normalized)
    if not match:
        return False
    major, minor, patch = (int(part) for part in match.groups())
    return (major, minor, patch) >= (4, 8, 0)


def pypi_install_smoke(
    *,
    package: str,
    version: str,
    python: str,
    check_new_user_path: bool,
    timeout: float,
) -> list[Check]:
    normalized = normalize_version(version)
    checks: list[Check] = []
    with tempfile.TemporaryDirectory(prefix="skillops-post-release-") as temp_dir:
        root = Path(temp_dir)
        venv = root / "venv"
        try:
            cp = run_command([python, "-m", "venv", str(venv)], timeout=timeout)
        except subprocess.TimeoutExpired:
            return [Check("pypi-install-venv", False, f"timed out after {timeout:.0f}s")]
        if cp.returncode != 0:
            return [Check("pypi-install-venv", False, cp.stderr.strip() or cp.stdout.strip())]

        py = venv / "bin" / "python"
        cli = venv / "bin" / "skills-orchestrator"
        try:
            install = run_command(
                [
                    str(py),
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    f"{package}=={normalized}",
                ],
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return [Check("pypi-install", False, f"timed out after {timeout:.0f}s")]
        checks.append(
            Check(
                "pypi-install",
                install.returncode == 0,
                "installed"
                if install.returncode == 0
                else (install.stderr or install.stdout).strip().splitlines()[-1],
            )
        )
        if install.returncode != 0:
            return checks

        try:
            version_cp = run_command([str(cli), "--version"], timeout=timeout)
        except subprocess.TimeoutExpired:
            return [*checks, Check("pypi-cli-version", False, f"timed out after {timeout:.0f}s")]
        checks.append(
            Check(
                "pypi-cli-version",
                version_cp.returncode == 0 and normalized in version_cp.stdout,
                version_cp.stdout.strip() or version_cp.stderr.strip(),
            )
        )
        try:
            pip_check = run_command([str(py), "-m", "pip", "check"], timeout=timeout)
        except subprocess.TimeoutExpired:
            return [*checks, Check("pypi-pip-check", False, f"timed out after {timeout:.0f}s")]
        checks.append(
            Check(
                "pypi-pip-check",
                pip_check.returncode == 0,
                pip_check.stdout.strip() or pip_check.stderr.strip(),
            )
        )

        if supports_optional_mcp_runtime(normalized):
            no_mcp_script = (
                "import importlib.util; "
                "raise SystemExit(0 if importlib.util.find_spec('mcp') is None else 1)"
            )
            try:
                no_mcp = run_command([str(py), "-c", no_mcp_script], timeout=timeout)
            except subprocess.TimeoutExpired:
                return [
                    *checks,
                    Check("pypi-default-without-mcp", False, f"timed out after {timeout:.0f}s"),
                ]
            checks.append(
                Check(
                    "pypi-default-without-mcp",
                    no_mcp.returncode == 0,
                    "default install does not include MCP runtime"
                    if no_mcp.returncode == 0
                    else "default install unexpectedly includes MCP runtime",
                )
            )

            try:
                mcp_hint = run_command(
                    [str(cli), "mcp-test", "list_skills", "{}"],
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return [
                    *checks,
                    Check("pypi-mcp-extra-hint", False, f"timed out after {timeout:.0f}s"),
                ]
            hint_output = f"{mcp_hint.stdout}\n{mcp_hint.stderr}"
            checks.append(
                Check(
                    "pypi-mcp-extra-hint",
                    mcp_hint.returncode != 0 and "skills-orchestrator[mcp]" in hint_output,
                    "missing MCP runtime shows skills-orchestrator[mcp] install hint"
                    if mcp_hint.returncode != 0 and "skills-orchestrator[mcp]" in hint_output
                    else hint_output.strip(),
                )
            )

        if check_new_user_path:
            project = root / "new-user"
            project.mkdir()
            commands = [
                (
                    "new-user-init",
                    [str(cli), "init", "--template", "team-standard", "--non-interactive"],
                ),
                (
                    "new-user-check",
                    [
                        str(cli),
                        "check",
                        "--policy-pack",
                        "builtin/team-standard",
                        "--fail-on",
                        "warning",
                    ],
                ),
                ("new-user-schema-audit", [str(cli), "schema", "audit", "--format", "json"]),
                (
                    "new-user-schema-audit-stable",
                    [str(cli), "schema", "audit", "--stability", "stable", "--format", "json"],
                ),
                ("new-user-build", [str(cli), "build", "--lock"]),
                (
                    "new-user-doctor",
                    [str(cli), "doctor", "--profile", "adopter", "--fail-under", "100"],
                ),
                (
                    "new-user-conformance",
                    [str(cli), "conformance", "run", "--profile", "core", "--format", "json"],
                ),
                ("new-user-evidence-export", [str(cli), "evidence", "export", "--out", "evidence"]),
                (
                    "new-user-evidence-schema",
                    [
                        str(cli),
                        "schema",
                        "validate",
                        "--kind",
                        "evidence",
                        "--input",
                        "evidence/evidence-manifest.json",
                    ],
                ),
            ]
            for check_name, command in commands:
                try:
                    cp = run_command(command, cwd=project, timeout=timeout)
                except subprocess.TimeoutExpired:
                    checks.append(
                        Check(
                            check_name,
                            False,
                            f"timed out after {timeout:.0f}s: {' '.join(command)}",
                        )
                    )
                    break
                checks.append(
                    Check(
                        check_name,
                        cp.returncode == 0,
                        cp.stdout.strip().splitlines()[-1]
                        if cp.stdout.strip()
                        else cp.stderr.strip(),
                    )
                )
                if cp.returncode != 0:
                    break
    return checks


def mcp_runtime_install_smoke(
    *,
    package: str,
    version: str,
    python: str,
    constraints: str | None,
    sbom_output: str | None,
    timeout: float,
) -> list[Check]:
    """Install the public MCP extra in isolation and exercise the real protocol path."""
    normalized = normalize_version(version)
    checks: list[Check] = []
    constraint_path = Path(constraints).resolve() if constraints else None
    if constraint_path is not None and not constraint_path.is_file():
        return [
            Check(
                "pypi-mcp-constraints",
                False,
                f"MCP constraints file does not exist: {constraint_path}",
            )
        ]

    with tempfile.TemporaryDirectory(prefix="skillops-post-release-mcp-") as temp_dir:
        root = Path(temp_dir)
        venv = root / "venv"
        try:
            cp = run_command([python, "-m", "venv", str(venv)], timeout=timeout)
        except subprocess.TimeoutExpired:
            return [Check("pypi-mcp-venv", False, f"timed out after {timeout:.0f}s")]
        if cp.returncode != 0:
            return [Check("pypi-mcp-venv", False, cp.stderr.strip() or cp.stdout.strip())]

        py = venv / "bin" / "python"
        cli = venv / "bin" / "skills-orchestrator"
        install_command = [
            str(py),
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
        ]
        if constraint_path is not None:
            install_command.extend(["--constraint", str(constraint_path)])
        install_command.append(f"{package}[mcp]=={normalized}")
        try:
            install = run_command(install_command, timeout=timeout)
        except subprocess.TimeoutExpired:
            return [Check("pypi-mcp-install", False, f"timed out after {timeout:.0f}s")]
        checks.append(
            Check(
                "pypi-mcp-install",
                install.returncode == 0,
                "isolated MCP extra installed"
                if install.returncode == 0
                else (install.stderr or install.stdout).strip().splitlines()[-1],
            )
        )
        if install.returncode != 0:
            return checks

        pip_check = run_command([str(py), "-m", "pip", "check"], timeout=timeout)
        checks.append(
            Check(
                "pypi-mcp-pip-check",
                pip_check.returncode == 0,
                pip_check.stdout.strip() or pip_check.stderr.strip(),
            )
        )

        project = root / "project"
        project.mkdir()
        init = run_command(
            [str(cli), "init", "--template", "team-standard", "--non-interactive"],
            cwd=project,
            timeout=timeout,
        )
        if init.returncode != 0:
            checks.append(
                Check(
                    "pypi-mcp-protocol",
                    False,
                    init.stderr.strip() or init.stdout.strip(),
                )
            )
        else:
            protocol = run_command(
                [str(cli), "mcp-test", "list_skills", "{}"],
                cwd=project,
                timeout=timeout,
            )
            checks.append(
                Check(
                    "pypi-mcp-protocol",
                    protocol.returncode == 0,
                    "mcp-test list_skills completed"
                    if protocol.returncode == 0
                    else protocol.stderr.strip() or protocol.stdout.strip(),
                )
            )

        versions_cp = run_command(
            [str(py), str(REPO_ROOT / "scripts" / "report_mcp_versions.py")],
            timeout=timeout,
        )
        try:
            versions = json.loads(versions_cp.stdout) if versions_cp.returncode == 0 else {}
        except json.JSONDecodeError:
            versions = {}
        required_versions = {"mcp", "starlette", "sse-starlette"}
        versions_ok = versions_cp.returncode == 0 and required_versions <= set(versions)
        checks.append(
            Check(
                "pypi-mcp-runtime-versions",
                versions_ok,
                json.dumps(versions, sort_keys=True)
                if versions_ok
                else versions_cp.stderr.strip() or versions_cp.stdout.strip(),
            )
        )

        sbom_path = root / "mcp-runtime-sbom.cdx.json"
        sbom_cp = run_command(
            [
                str(cli),
                "supply-chain",
                "sbom",
                "--installed-environment",
                "--output",
                str(sbom_path),
            ],
            timeout=timeout,
        )
        sbom_names: set[str] = set()
        if sbom_cp.returncode == 0 and sbom_path.is_file():
            try:
                sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
                sbom_names = {
                    str(component.get("name", "")).lower()
                    for component in sbom.get("components", [])
                }
            except (json.JSONDecodeError, OSError):
                sbom_names = set()
        required_sbom_names = {"mcp", "starlette", "sse-starlette"}
        missing_sbom_names = sorted(required_sbom_names - sbom_names)
        sbom_ok = sbom_cp.returncode == 0 and not missing_sbom_names
        if sbom_ok and sbom_output:
            destination = Path(sbom_output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sbom_path, destination)
        checks.append(
            Check(
                "pypi-mcp-runtime-sbom",
                sbom_ok,
                "CycloneDX SBOM contains mcp, starlette, and sse-starlette"
                if sbom_ok
                else f"missing components: {missing_sbom_names}",
            )
        )
    return checks


def pypi_hash_locked_install_smoke(
    *,
    package: str,
    version: str,
    python: str,
    timeout: float,
) -> list[Check]:
    """Verify a released package can install from a local wheelhouse with pip hashes."""
    normalized = normalize_version(version)
    checks: list[Check] = []
    with tempfile.TemporaryDirectory(prefix="skillops-hash-lock-") as temp_dir:
        root = Path(temp_dir)
        wheelhouse = root / "wheelhouse"
        wheelhouse.mkdir()
        lock_file = root / "requirements.lock"
        try:
            download = run_command(
                [
                    python,
                    "-m",
                    "pip",
                    "download",
                    "--only-binary=:all:",
                    "--dest",
                    str(wheelhouse),
                    f"{package}=={normalized}",
                ],
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return [Check("pypi-hash-lock-download", False, f"timed out after {timeout:.0f}s")]
        wheels = sorted(wheelhouse.glob("*.whl"))
        checks.append(
            Check(
                "pypi-hash-lock-download",
                download.returncode == 0 and bool(wheels),
                f"downloaded {len(wheels)} wheels"
                if download.returncode == 0
                else (download.stderr or download.stdout).strip(),
            )
        )
        if download.returncode != 0 or not wheels:
            return checks

        try:
            lock_file.write_text(
                "\n".join(wheel_requirement_line(path) for path in wheels) + "\n",
                encoding="utf-8",
            )
        except ValueError as exc:
            return [*checks, Check("pypi-hash-lock-file", False, str(exc))]
        checks.append(
            Check(
                "pypi-hash-lock-file",
                True,
                f"generated {lock_file.name} with {len(wheels)} hashes",
            )
        )

        venv = root / "venv"
        try:
            cp = run_command([python, "-m", "venv", str(venv)], timeout=timeout)
        except subprocess.TimeoutExpired:
            return [
                *checks,
                Check("pypi-hash-lock-venv", False, f"timed out after {timeout:.0f}s"),
            ]
        if cp.returncode != 0:
            return [
                *checks,
                Check("pypi-hash-lock-venv", False, cp.stderr.strip() or cp.stdout.strip()),
            ]

        py = venv / "bin" / "python"
        cli = venv / "bin" / "skills-orchestrator"
        try:
            install = run_command(
                [
                    str(py),
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--find-links",
                    str(wheelhouse),
                    "--require-hashes",
                    "-r",
                    str(lock_file),
                ],
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return [
                *checks,
                Check("pypi-hash-lock-install", False, f"timed out after {timeout:.0f}s"),
            ]
        checks.append(
            Check(
                "pypi-hash-lock-install",
                install.returncode == 0,
                "installed from local wheelhouse with --require-hashes"
                if install.returncode == 0
                else (install.stderr or install.stdout).strip().splitlines()[-1],
            )
        )
        if install.returncode != 0:
            return checks

        try:
            version_cp = run_command([str(cli), "--version"], timeout=timeout)
        except subprocess.TimeoutExpired:
            return [
                *checks,
                Check("pypi-hash-lock-cli-version", False, f"timed out after {timeout:.0f}s"),
            ]
        checks.append(
            Check(
                "pypi-hash-lock-cli-version",
                version_cp.returncode == 0 and normalized in version_cp.stdout,
                version_cp.stdout.strip() or version_cp.stderr.strip(),
            )
        )

        try:
            pip_check = run_command([str(py), "-m", "pip", "check"], timeout=timeout)
        except subprocess.TimeoutExpired:
            return [
                *checks,
                Check("pypi-hash-lock-pip-check", False, f"timed out after {timeout:.0f}s"),
            ]
        checks.append(
            Check(
                "pypi-hash-lock-pip-check",
                pip_check.returncode == 0,
                pip_check.stdout.strip() or pip_check.stderr.strip(),
            )
        )
    return checks


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_source_checks(args: argparse.Namespace) -> list[Check]:
    """Fail closed when release evidence is not bound to the verified tag source."""
    verified = str(getattr(args, "verified_target_sha", "") or "").lower()
    checked_out = str(getattr(args, "checked_out_sha", "") or "").lower()
    expected_constraints = str(getattr(args, "constraints_sha256", "") or "").lower()
    if not any((verified, checked_out, expected_constraints)):
        return []

    checks = [
        Check(
            "release-source-identifiers",
            bool(COMMIT_SHA_RE.fullmatch(verified) and COMMIT_SHA_RE.fullmatch(checked_out)),
            f"verified_target_sha={verified!r}, checked_out_sha={checked_out!r}",
        ),
        Check(
            "release-source-match",
            bool(verified and checked_out and verified == checked_out),
            f"verified_target_sha={verified!r}, checked_out_sha={checked_out!r}",
        ),
    ]

    constraints_path = Path(
        getattr(args, "mcp_constraints", None) or REPO_ROOT / "constraints-mcp.txt"
    )
    actual_constraints = sha256_file(constraints_path) if constraints_path.is_file() else ""
    checks.append(
        Check(
            "release-constraints-digest",
            bool(
                SHA256_RE.fullmatch(expected_constraints)
                and actual_constraints
                and expected_constraints == actual_constraints
            ),
            (
                f"constraints_sha256={actual_constraints!r}, "
                f"expected={expected_constraints!r}, path={str(constraints_path)!r}"
            ),
        )
    )
    return checks


def release_metadata(args: argparse.Namespace) -> dict[str, str]:
    """Return source-binding fields retained in the machine-readable report."""
    metadata = {
        "release_tag": tag_for_version(args.version),
        "package_version": normalize_version(args.version),
    }
    optional = {
        "verified_target_sha": str(getattr(args, "verified_target_sha", "") or "").lower(),
        "checked_out_sha": str(getattr(args, "checked_out_sha", "") or "").lower(),
        "constraints_sha256": str(getattr(args, "constraints_sha256", "") or "").lower(),
    }
    metadata.update({key: value for key, value in optional.items() if value})
    return metadata


def print_checks(
    checks: list[Check],
    *,
    as_json: bool,
    metadata: dict[str, str] | None = None,
) -> None:
    if as_json:
        print(json.dumps(build_report(checks, metadata=metadata), indent=2, ensure_ascii=False))
        return

    status = "pass" if all(check.ok for check in checks) else "fail"
    print(f"Post-release smoke: {status}")
    print(
        f"Summary: {sum(1 for check in checks if check.ok)} passed, {sum(1 for check in checks if not check.ok)} failed"
    )
    for check in checks:
        marker = "OK" if check.ok else "FAIL"
        print(f"[{marker}] {check.name}: {check.message}")


def build_report(
    checks: list[Check],
    *,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the machine-readable post-release smoke report."""
    report = {
        "schema_version": "skills-orchestrator.post-release-smoke.v1",
        "status": "pass" if all(check.ok for check in checks) else "fail",
        "summary": {
            "passed": sum(1 for check in checks if check.ok),
            "failed": sum(1 for check in checks if not check.ok),
        },
        "checks": [check.as_dict() for check in checks],
    }
    if metadata:
        report.update(metadata)
    return report


def collect_checks(args: argparse.Namespace) -> list[Check]:
    checks = release_source_checks(args)
    version = normalize_version(args.version)
    tag = tag_for_version(version)
    ghcr_digest: str | None = None

    if not args.skip_github:
        try:
            release = fetch_json(
                f"https://api.github.com/repos/{args.repo}/releases/tags/{tag}",
                timeout=args.timeout,
                token=github_token_from_env(),
            )
            checks.extend(github_release_check(release, version=version))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            checks.append(Check("github-release-fetch", False, str(exc)))

    if not args.skip_pypi:
        try:
            project = fetch_json(f"https://pypi.org/pypi/{args.package}/json", timeout=args.timeout)
            checks.extend(pypi_release_check(project, package=args.package, version=version))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            checks.append(Check("pypi-json-fetch", False, str(exc)))

    if not args.skip_ghcr:
        if not shutil.which("docker"):
            checks.append(Check("ghcr-docker-cli", False, "docker CLI is not available"))
        else:
            ref = f"{args.image}:{tag}"
            try:
                cp = run_command(
                    ["docker", "buildx", "imagetools", "inspect", ref],
                    timeout=args.timeout,
                )
            except subprocess.TimeoutExpired:
                checks.append(Check("ghcr-manifest-inspect", False, f"timed out inspecting {ref}"))
            else:
                if cp.returncode != 0:
                    checks.append(
                        Check(
                            "ghcr-manifest-inspect", False, cp.stderr.strip() or cp.stdout.strip()
                        )
                    )
                else:
                    digest, _, _ = parse_imagetools_output(cp.stdout)
                    ghcr_digest = digest
                    checks.extend(
                        ghcr_manifest_check(
                            cp.stdout,
                            required_platforms=set(args.require_platform),
                            require_attestations=not args.no_ghcr_attestations,
                        )
                    )
                    if args.check_ghcr_signature:
                        if digest is None:
                            checks.append(
                                Check(
                                    "ghcr-cosign-signature",
                                    False,
                                    f"could not resolve digest for {ref}",
                                )
                            )
                        else:
                            checks.extend(
                                ghcr_signature_check(
                                    image=args.image,
                                    digest=digest,
                                    repo=args.repo,
                                    timeout=args.timeout,
                                )
                            )
                    if args.check_ghcr_os_sbom:
                        if digest is None:
                            checks.append(
                                Check(
                                    "ghcr-os-sbom-attestation",
                                    False,
                                    f"could not resolve digest for {ref}",
                                )
                            )
                        else:
                            checks.extend(
                                ghcr_os_sbom_attestation_check(
                                    image=args.image,
                                    digest=digest,
                                    repo=args.repo,
                                    version=version,
                                    timeout=args.timeout,
                                )
                            )

    if args.check_slsa_readiness:
        if ghcr_digest is None:
            checks.append(
                Check(
                    "slsa-readiness-report",
                    False,
                    "could not resolve GHCR digest for SLSA readiness subject",
                )
            )
        else:
            checks.extend(
                slsa_readiness_report_check(
                    version=version,
                    repo=args.repo,
                    image=args.image,
                    digest=ghcr_digest,
                )
            )

    if args.check_pypi_install:
        checks.extend(
            pypi_install_smoke(
                package=args.package,
                version=version,
                python=args.python,
                check_new_user_path=args.check_new_user_path,
                timeout=max(args.timeout, 300),
            )
        )

    if args.check_pypi_hash_lock:
        checks.extend(
            pypi_hash_locked_install_smoke(
                package=args.package,
                version=version,
                python=args.python,
                timeout=max(args.timeout, 300),
            )
        )

    if getattr(args, "check_mcp_runtime", False):
        checks.extend(
            mcp_runtime_install_smoke(
                package=args.package,
                version=version,
                python=args.python,
                constraints=getattr(args, "mcp_constraints", None),
                sbom_output=getattr(args, "mcp_sbom_output", None),
                timeout=max(args.timeout, 300),
            )
        )

    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", required=True, help="Release version, with or without leading v."
    )
    parser.add_argument("--repo", default="BambooGap/skills-orchestrator")
    parser.add_argument("--package", default="skills-orchestrator")
    parser.add_argument("--image", default="ghcr.io/bamboogap/skills-orchestrator")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--skip-github", action="store_true")
    parser.add_argument("--skip-pypi", action="store_true")
    parser.add_argument("--skip-ghcr", action="store_true")
    parser.add_argument("--check-pypi-install", action="store_true")
    parser.add_argument("--check-pypi-hash-lock", action="store_true")
    parser.add_argument("--check-mcp-runtime", action="store_true")
    parser.add_argument("--mcp-constraints", default=None)
    parser.add_argument("--mcp-sbom-output", default=None)
    parser.add_argument("--verified-target-sha", default=None)
    parser.add_argument("--checked-out-sha", default=None)
    parser.add_argument("--constraints-sha256", default=None)
    parser.add_argument("--check-ghcr-signature", action="store_true")
    parser.add_argument("--check-ghcr-os-sbom", action="store_true")
    parser.add_argument("--check-slsa-readiness", action="store_true")
    parser.add_argument("--check-new-user-path", action="store_true")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--require-platform", action="append", default=["linux/amd64", "linux/arm64"]
    )
    parser.add_argument("--no-ghcr-attestations", action="store_true")
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-delay", type=float, default=15)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    if args.retries < 1:
        parser.error("--retries must be >= 1")
    if args.retry_delay < 0:
        parser.error("--retry-delay must be >= 0")

    checks: list[Check] = []
    for attempt in range(1, args.retries + 1):
        checks = collect_checks(args)
        if all(check.ok for check in checks):
            break
        if attempt < args.retries:
            if args.format == "text":
                print(
                    f"Post-release smoke attempt {attempt}/{args.retries} failed; "
                    f"retrying in {args.retry_delay:g}s...",
                    file=sys.stderr,
                )
            time.sleep(args.retry_delay)

    print_checks(
        checks,
        as_json=args.format == "json",
        metadata=release_metadata(args),
    )
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
