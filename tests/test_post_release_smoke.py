from scripts.post_release_smoke import (
    ghcr_manifest_check,
    github_release_check,
    parse_imagetools_output,
    pypi_release_check,
)


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
