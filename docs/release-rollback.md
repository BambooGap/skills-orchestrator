# Release Rollback Playbook

Use this playbook when a published SkillOps release is wrong, incomplete, or unsafe. The default
response is to publish a fixed patch release and document the incident. Do not rewrite published
history unless a secret or actively exploitable artifact was exposed.

## Severity Levels

| Level | Example | Default response |
| --- | --- | --- |
| S0: compromised | leaked credential, malicious artifact, compromised workflow token | Remove exposed secret, revoke token, publish advisory, consider deleting affected release assets. |
| S1: unsafe artifact | broken package, wrong container digest, invalid attestation, severe runtime bug | Yank PyPI release, mark GitHub Release as withdrawn, publish fixed patch release. |
| S2: contract mismatch | README/docs point at wrong tag, schema/version mismatch, failed evidence validation | Publish patch release with corrected docs/artifacts. |
| S3: cosmetic | typo, stale prose, non-contract docs issue | Fix on main; release only if the GitHub Release or PyPI page is misleading. |

## First 10 Minutes

1. Stop any in-progress release workflow if it is still running.
2. Capture facts:
   - release tag,
   - target commit,
   - PyPI version,
   - GHCR image digest,
   - failing command,
   - affected schema or artifact.
3. Open or update a tracking issue.
4. Decide severity using the table above.
5. Avoid deleting evidence before you have copied the failing logs or artifact hashes.

## PyPI Response

PyPI versions cannot be safely overwritten. Prefer yanking a bad release over deleting it:

```bash
python3.12 -m pip install twine
twine yank skills-orchestrator==<bad-version> \
  --reason "Use <fixed-version>; <short reason>"
```

Then publish a new patch version:

```bash
# bump pyproject.toml and skills_orchestrator/__init__.py
# update CHANGELOG.md
gh release create vX.Y.Z --target <fixed-commit> --title "vX.Y.Z" --notes-file release-notes.md
```

Never reuse a yanked version number.

## GitHub Release Response

For S1 or S2 incidents:

1. Edit the GitHub Release notes for the bad version.
2. Add a visible warning at the top:

   ```markdown
   > Withdrawn: use vX.Y.Z. Reason: ...
   ```

3. Do not move the existing tag.
4. Publish a new patch release from a new commit.

For S0 incidents, follow the security policy first. If release assets contain secrets or malicious
content, remove the exposed asset and document the removal in the issue and advisory.

## GHCR Response

Container tags are mutable in some registries, but this project treats release tags as immutable.
Default response:

1. Publish a fixed patch tag.
2. Keep the bad tag available unless it is S0 or actively dangerous.
3. Document the bad digest and fixed digest.
4. Update docs and examples to the fixed tag.

Validate the fixed image:

```bash
docker manifest inspect ghcr.io/bamboogap/skills-orchestrator:<fixed-version>

docker run --rm ghcr.io/bamboogap/skills-orchestrator:<fixed-version> --version
```

## Evidence Regeneration

After a fixed patch release, regenerate release evidence:

```bash
skills-orchestrator evidence export --config config/skills.yaml --out evidence
skills-orchestrator schema audit --stability all --format text
skills-orchestrator conformance run \
  --config config/skills.yaml \
  --profile enterprise \
  --policy-pack builtin/engineering-grade
skills-orchestrator doctor --profile enterprise --fail-under 100
```

Attach or link the relevant evidence bundle in the issue or release notes.

## Communication Template

```markdown
## Release incident: vX.Y.Z

Status: withdrawn | fixed | monitoring
Severity: S0 | S1 | S2 | S3
Affected surfaces: PyPI | GHCR | GitHub Release | docs | schema

### What happened

### Impact

### Detection

### Mitigation

### Fixed version

### Verification
```

## Exit Criteria

An incident is closed when:

- the fixed patch release is published,
- PyPI latest points at the fixed version,
- GHCR manifest exists for the fixed version,
- GitHub Release latest points at the fixed version,
- clean PyPI install passes,
- `schema audit --stability all`, `conformance run`, and `doctor --profile enterprise` pass,
- docs no longer point at the withdrawn release.
