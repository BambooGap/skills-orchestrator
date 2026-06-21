# skills-orchestrator v3.2.0 Test Report

Date: 2026-06-21

## Scope

This report covers the v3.2.0 Trust Metadata Pack:

- skill `license` metadata across parser, schemas, registry, manifest, CycloneDX, OPA input, and
  evidence bundles
- external import `provenance` capture with observed source URL, ref, commit, content hash, and
  fetch timestamp
- engineering-grade diagnostics `SO018`, `SO019`, and `SO020`
- safer GitHub import boundaries for HTTPS-only sources, no userinfo/query/fragment URLs,
  no-redirect raw downloads, and path-safe filenames
- engineering-grade demo repository flow

## Verification

| Check | Result |
| --- | --- |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest -q` | PASS, 449 passed |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m ruff check skills_orchestrator tests` | PASS |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m ruff format --check skills_orchestrator tests` | PASS |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator --version` | PASS, `skills-orchestrator, version 3.2.0` |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest -q tests/test_version.py` | PASS |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator check --config config/skills.yaml --policy-pack builtin/engineering-grade --fail-on warning` | PASS, 20 configured skills, 0 findings |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator conformance run --config config/skills.yaml --policy-pack builtin/engineering-grade --profile core` | PASS, 9 passed |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator doctor --profile adopter --config config/skills.yaml --fail-under 80` | PASS, 100/100 |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator schema validate --kind config --input config/skills.yaml` | PASS |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator registry build --config-glob config/skills.yaml --output /tmp/skill-registry-v3.2.0.json` | PASS, 19 default-zone registry skills |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator schema validate --kind registry --input /tmp/skill-registry-v3.2.0.json` | PASS |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator evidence export --config config/skills.yaml --out /tmp/skillops-evidence-v3.2.0` | PASS |
| `schema validate` for `/tmp/skillops-evidence-v3.2.0/{evidence-manifest,instruction-manifest,policy-opa-input,skill-registry}.json` | PASS |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator supply-chain sbom --output /tmp/package-sbom-v3.2.0.cdx.json` | PASS |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/skills-orchestrator schema validate --kind supply-chain-sbom --input /tmp/package-sbom-v3.2.0.cdx.json` | PASS |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m build` | PASS, built `skills_orchestrator-3.2.0.tar.gz` and wheel |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m twine check dist/skills_orchestrator-3.2.0*` | PASS |
| `examples/demo-repo`: `check --policy-pack builtin/engineering-grade --fail-on warning` | PASS, 2 skills, 0 findings |
| `examples/demo-repo`: registry build, evidence export, and schema validate for evidence/registry/manifest/OPA input | PASS |
| `examples/demo-repo`: `adapters inspect` plus adapter-inspect schema validation | PASS |

## Review Fixes

- Removed unreviewed external skills from the default root `skill_dirs`; `skills/external` is now
  excluded until license and provenance review is complete.
- Kept `NOASSERTION` for the external Karpathy example instead of claiming MIT/Apache-2.0, so the
  built-in allowlist remains fail-closed.
- Changed importer-generated config entries so observed `source` and `provenance` cannot be
  overridden by remote frontmatter.
- Fixed import provenance so repository, tree, and blob imports resolve the requested branch or tag
  to a commit first, then fetch contents and raw bytes through that immutable commit.
- Fixed bare repository imports for repositories whose default branch is not `main`.
- Rejected mutable `raw.githubusercontent.com` refs for direct raw imports; raw direct imports must
  use a full 40-character commit SHA.
- Made external-source detection case-insensitive so `HTTPS://...` cannot bypass `SO020`.

## Skipped

| Check | Reason |
| --- | --- |
| `pip-audit` | Not installed in the current local environment. |
| `python -m pip check` | The current `.venv` does not include the `pip` module. |

## Notes

`check` reports 20 configured skills because it validates all configured metadata. The root registry
build reports 19 skills because it is scoped to the default zone; `chinese-code-review` belongs to
the enterprise zone.
