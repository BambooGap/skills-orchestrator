# Security Policy

## Reporting Vulnerabilities

Private vulnerability reporting is enabled for this repository. Please use GitHub's private
vulnerability reporting flow instead of opening a public issue with exploit details.

If private reporting is unavailable for your account, open a public issue titled
`security contact request` with only a high-level summary and no exploit details. A maintainer will
move the discussion to a private channel.

## Supported Versions

Security fixes target the latest released minor line. Older tags remain available for audit, but
the project does not currently maintain multiple long-term support branches.

## Trust Boundaries

Skills Orchestrator is a local CLI, GitHub Action, and optional MCP server. It does not provide a
hosted multi-tenant service in the open-source core.

Trusted inputs:

- local repository files reviewed by the user or CI,
- `config/skills.yaml`,
- Markdown skill files under configured `skill_dirs`,
- CI-provided GitHub tokens with least-privilege permissions.

Untrusted or semi-trusted inputs:

- imported GitHub skill files,
- pull request changes from forks,
- MCP tool arguments supplied by an agent,
- generated evidence artifacts received from another repository.

## MCP Skill Trust Model

The MCP server returns skill metadata and skill content from configured local files. It does not
execute skill Markdown. The risk is instruction injection or untrusted guidance being routed into an
agent context.

Security controls:

- Use `check` and `builtin/team-standard` before enabling runtime MCP routing.
- Treat imported skills as untrusted until reviewed.
- Keep `--max-content-bytes` bounded for shared environments. Use `--max-content-bytes 0` only for
  trusted local debugging.
- Do not put secrets, credentials, private customer data, or production incident data into skill
  Markdown.
- Use zones and `conflict_with` to avoid mixing incompatible instruction sets.

## Runtime Audit And HMAC

MCP audit logging is opt-in:

```bash
skills-orchestrator serve --config config/skills.yaml --audit-dir .skills-audit
```

Audit logs are JSONL at `.skills-audit/events.jsonl`. They record tool names, argument keys,
outcomes, routing decisions, result counts, and active skill ids. They do not store raw task text or
skill content.

By default, task text is represented by unsalted SHA-256 for local correlation. For shared logs,
set a private salt to use HMAC-SHA256:

```bash
export SKILLS_ORCHESTRATOR_AUDIT_SALT="$(openssl rand -hex 32)"
```

The salt must be treated as sensitive operational material. Rotating the salt breaks cross-period
task hash correlation, which is usually desirable for privacy.

## Import Provenance Boundary

`skills-orchestrator import` only accepts HTTPS GitHub URLs from `github.com` or
`raw.githubusercontent.com`. The importer rejects userinfo, query strings,
fragments, non-GitHub download URLs, and HTTP redirects. Imported content is size-bounded, must be
UTF-8 text, and must have valid frontmatter syntax when frontmatter is present.

Import records observed source and provenance in `skills.yaml`: canonical source URL, requested
ref, resolved commit, fetched content hash, and fetch timestamp. Frontmatter inside the imported
file cannot override this observed `source` or `provenance`.

Repository and `github.com/.../tree|blob/...` imports resolve the requested branch or tag to a
commit first, then fetch contents through that immutable commit. Direct `raw.githubusercontent.com`
imports must already use a full 40-character commit SHA; mutable raw refs such as `main`, `master`,
or `feature/foo` are rejected.

Import does not prove author identity, repository ownership, license compatibility, or semantic
safety. `builtin/engineering-grade` fails closed for unallowlisted licenses and requires provenance
for HTTP(S)-sourced skills, but legal and semantic review remain human responsibilities.

Recommended review steps:

```bash
skills-orchestrator import <github-url> --dry-run
skills-orchestrator check --config config/skills.yaml --policy-pack builtin/engineering-grade
git diff -- skills/ config/skills.yaml
```

## GitHub Action Permissions

Use the least permissions required by selected features:

```yaml
permissions:
  contents: read
  security-events: write   # only when upload-sarif: true
  pull-requests: write     # only when comment-registry-diff: true
```

The action should not be run with broad repository write permissions unless another workflow step
requires them.

For untrusted fork pull requests, avoid `pull_request_target` unless the workflow does not check out
or execute untrusted code.

## Secrets

The CLI and MCP server should not log secrets. If you find a command path that logs tokens,
authorization headers, cookies, private keys, passwords, or raw task content in audit logs, report it
as a vulnerability.
