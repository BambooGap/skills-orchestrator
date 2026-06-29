# Manifest Export Examples

Generate the native instruction inventory:

```bash
skills-orchestrator manifest \
  --config config/skills.yaml \
  --format json \
  --include-diagnostics \
  --output instruction-manifest.json
```

Generate a CycloneDX interoperability adapter:

```bash
skills-orchestrator manifest \
  --config config/skills.yaml \
  --format cyclonedx \
  --package team-agent-instructions \
  --output instruction-manifest.cdx.json
```

Use the native JSON manifest as the authoritative review artifact. Use CycloneDX when an existing
SBOM or supply-chain tool expects BOM-shaped input.
