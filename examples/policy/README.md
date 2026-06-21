# Policy Export Examples

Skills Orchestrator does not use OPA as a runtime backend. The built-in resolver remains the
authoritative decision system for zones, load policies, priorities, and conflicts.

These exports exist so teams can inspect resolver facts with policy-as-code tools:

```bash
skills-orchestrator policy export \
  --config config/skills.yaml \
  --format opa-input \
  --output policy-input.json
```

```bash
skills-orchestrator policy export \
  --config config/skills.yaml \
  --format rego-test \
  --output skills_orchestrator_policy_test.rego
```

If OPA is installed locally, the generated Rego fixture can be checked with:

```bash
opa test skills_orchestrator_policy_test.rego
```

The generated tests verify that exported skill statuses match the resolver output and that
`effective_load_policy` maps to forced skills for the selected zone.

For the complete artifact authority model, see
[Manifest And Policy Exports](../../docs/manifest-policy-exports.md).

## Declarative Policy Pack Example

`engineering-grade-pack.yaml` is a safe local policy pack. It is data-only YAML and does not execute
repository code.

```bash
skills-orchestrator schema validate \
  --kind policy-pack \
  --input examples/policy/engineering-grade-pack.yaml

skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack examples/policy/engineering-grade-pack.yaml
```
