# Subagent Spawn Heuristics

Mirrors the `should-spawn-*.js` scripts in the action. Apply each to the changed-file list (paths + status) and patch text. Each produces `{ spawn, reason }`. Evaluate rules **top to bottom; first match wins**.

Inputs per file: `filename`, `status` (`added`/`modified`/`removed`), `patch` (the diff hunk text). Labels don't exist locally — treat the `skip-review` / `breaking` label rules as N/A unless the user explicitly says "skip review" or "this is a breaking change". The user can force any agent on ("force breaking changes", "force license", "force data classification").

## Shared skip patterns

- **Docs-only:** every changed file matches `/\.(md|txt|rst|adoc)$/i` → skip the breaking-changes and data-classification agents.
- **Test-only:** every changed file matches `/(\/__tests__\/|\.test\.|\.spec\.|test\/|tests\/|__mocks__\/)/i` → skip breaking-changes and data-classification.

(License compliance has its own narrow trigger and ignores the docs/test skips.)

## 1. Breaking changes (`brk-`)

1. User says skip → `spawn: false`.
2. Forced → `spawn: true` ("forced via input").
3. No files → `spawn: false`.
4. User flags it breaking → `spawn: true` ("breaking label").
5. All docs-only → `spawn: false`. All test-only → `spawn: false`.
6. Otherwise collect signals; if any present → `spawn: true` with the joined reasons:
   - `action.yml` files: `/action\.ya?ml$/i`
   - workflow files: `/\.github\/workflows\/.*\.ya?ml$/`
   - package manifests: `/package\.json$|go\.mod$|setup\.py$|pyproject\.toml$|Cargo\.toml$/`
   - type definitions: `/\.d\.ts$|types?\.(ts|js)$|interfaces?\.(ts|js)$/i`
   - API routes: `/routes?\.[jt]sx?$|controllers?\.[jt]sx?$|handlers?\.[jt]sx?$|api\//i`
   - schema/migration files: `/schema|migration|\.sql$/i`
   - **removed files:** any file with `status === 'removed'`
   - **breaking-change keywords in patch** (case-insensitive): `inputs:`, `outputs:`, `required:`, `default:`, `deprecated`, `export (default )?(function|class|const|interface|type|enum)`, `module.exports`, `"main"`, `"exports"`, `"bin"`, `"engines"`, `"peerDependencies"`
7. No signals → `spawn: false`.

## 2. License compliance (`lic-`)

1. Forced → `spawn: true`.
2. User says skip → `spawn: false`.
3. No files → `spawn: false`.
4. `spawn: true` if any changed file's **basename** is a dependency manifest or lockfile:
   - npm: `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`
   - Go: `go.mod`, `go.sum`
   - Rust: `Cargo.toml`, `Cargo.lock`
   - Python: `pyproject.toml`, `setup.py`, `setup.cfg`, and `requirements*.txt`
   - Ruby: `Gemfile`, `Gemfile.lock`
   - PHP: `composer.json`
   - Java/Kotlin: `build.gradle`, `pom.xml`
   - Reason: `Dependency files changed: <basename> (<ecosystem>), ...`
5. Else → `spawn: false`. (Docs/test skips do **not** apply here.)

## 3. Data classification (`dcl-`)

1. Forced → `spawn: true`.
2. User says skip → `spawn: false`.
3. No files → `spawn: false`.
4. All docs-only → `spawn: false`. All test-only → `spawn: false`.
5. Collect signals; if any present → `spawn: true`:
   - Terraform/IaC files: `/\.tf$|\.tfvars$/`
   - Kubernetes/Helm configs: `/\.(ya?ml)$/i` **AND** path matches `/k8s|kubernetes|helm|chart|deploy|manifests?/i` (a generic `.yml` like a CI workflow does **not** trigger)
   - CloudFormation templates: `/cloudformation|cfn/i`
   - environment/secret files: `/(^|\/)\.env|secret|credential/i`
   - database/schema files: `/migration|schema|model/i`
   - API route/handler files: `/routes?\.[jt]sx?$|controllers?\.[jt]sx?$|handlers?\.[jt]sx?$|middleware\.[jt]sx?$|api\//i`
   - **sensitive keywords in patch** (case-insensitive): `password`, `secret`, `api_key`/`apiKey`, `private_key`/`privateKey`, `credential`, `token`, `encrypt`, `decrypt`, `kms`, `AES`, `TLS`, `email`, `phone`, `ssn`, `date_of_birth`/`dateOfBirth`, `personal`, `pii`, `gdpr`, `console.log`, `logger.`, `log.`, `logging`
6. No signals → `spawn: false`.
