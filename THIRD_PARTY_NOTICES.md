# Third-Party Notices

This file summarizes the main third-party packages used by the open-source CLI and development
tooling. It is not a replacement for generated SBOMs. Release verification should continue to use
the project SBOM and GHCR image SBOM attestations described in `docs/supply-chain-verification.md`.

## Runtime Dependencies

| Package | Purpose | Declared constraint |
| --- | --- | --- |
| Click | CLI framework | `click>=8.0` |
| jsonschema | JSON Schema validation | `jsonschema>=4.20` |
| PyYAML | YAML parsing | `pyyaml>=6.0` |

## Optional Runtime Dependencies

| Package | Purpose | Declared constraint |
| --- | --- | --- |
| MCP | Optional MCP server and local MCP test surfaces | `mcp>=1.0` |

## Development And Release Tooling

| Package | Purpose |
| --- | --- |
| build | Build wheel and sdist artifacts |
| pytest | Test runner |
| pytest-benchmark | Optional benchmark support |
| ruff | Lint and format checks |
| twine | Package metadata checks |

## Machine-Readable Evidence

Generate package SBOM evidence with:

```bash
skills-orchestrator supply-chain sbom --format cyclonedx-json --output evidence/package-sbom.cdx.json
```

Release images also publish GHCR attestations for package SBOM, OS/image SBOM, provenance, and
Cosign signature verification.
