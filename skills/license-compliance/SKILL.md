---
name: license-compliance
description: Scans project dependencies for license compliance across 9 ecosystems — JS/TS (pnpm/npm/yarn), Rust (cargo), Python (pip/poetry/uv/pipenv), Swift (SPM), Kotlin (Gradle), Dart (pub), Go (modules), C# (NuGet), and Solidity (Foundry). Classifies licenses as permissive, weak copyleft, or restrictive. Supports monorepos, remote GitHub repos, and org-wide scanning with tracker-based resume. Use when checking license compliance, preparing for audits, evaluating new dependencies, or running org-wide license sweeps.
---

# License Compliance Check

## Goal

Scan a project's dependencies and generate a license compliance report, classifying each dependency as permissive (OK), weak copyleft (MEDIUM), or restrictive (HIGH). Supports 9 ecosystems: JS/TS (pnpm/npm/yarn), Rust (cargo), Python (pip/poetry/uv/pipenv), Swift (SPM), Kotlin (Gradle), Dart (pub), Go (modules), C# (NuGet), and Solidity (Foundry).

## When to use

- Checking license compliance before shipping
- Evaluating a new dependency or library
- Preparing for security/legal audits
- Reviewing a project you don't own (use `--repo` mode)
- Replacing Snyk license compliance checks
- Org-wide license sweeps across multiple GitHub orgs (use `--org` mode)
- Tracking license compliance posture over time
- Scanning Rust crates for license compliance (via `cargo metadata`)
- Scanning Python packages for license compliance (via lockfile + PyPI)

## When not to use

- Unsupported ecosystems (Ruby/Bundler, PHP/Composer, Java/Maven, Scala/sbt, Elixir/Mix, etc.)
- Checking for security vulnerabilities (use `/github-dependabot-report` instead)

## Inputs

- A project directory with a supported lockfile, OR a GitHub `org/repo` reference
  - **JS/TS:** `pnpm-lock.yaml`, `package-lock.json`, or `yarn.lock`
  - **Rust:** `Cargo.lock` or `Cargo.toml`
  - **Python:** `poetry.lock`, `uv.lock`, `Pipfile.lock`, or `requirements.txt`
  - **Swift:** `Package.resolved`
  - **Kotlin:** `gradle/libs.versions.toml` or `build.gradle.kts`
  - **Dart:** `pubspec.lock` or `pubspec.yaml`
  - **Go:** `go.sum` or `go.mod`
  - **C#:** `Directory.Packages.props` or `*.csproj`
  - **Solidity:** `foundry.toml`
- Optional: `--prod-only` to skip devDependencies (JS/TS and Python only; Rust treats all deps as prod)
- Optional: `--repo org/repo` for remote scanning
- Optional: `--ref branch-name` to scan a specific branch

## Outputs

- Formatted markdown compliance report displayed to user

## Default workflow

### Step 1: Run the scanner

The scanner auto-detects the project type based on lockfiles/manifest files present.

For a local project:
```bash
python3 ~/.claude/skills/license-compliance/scripts/license_check.py --path /path/to/project --verbose 2>/dev/null
```

For a remote GitHub repo (works for any supported ecosystem):
```bash
python3 ~/.claude/skills/license-compliance/scripts/license_check.py --repo org/repo --verbose 2>/dev/null
```

For production dependencies only (JS/TS and Python):
```bash
python3 ~/.claude/skills/license-compliance/scripts/license_check.py --path /path/to/project --prod-only --verbose 2>/dev/null
```

**Ecosystem notes:**
- **JS/TS:** Requires `pnpm`, `npm`, or `yarn` installed. Runs install + `ls --json` to extract licenses.
- **Rust:** Requires `cargo` installed. Uses `cargo metadata` — no build needed. All deps treated as prod (Rust doesn't distinguish dev deps in metadata).
- **Python:** No tools required beyond Python. Parses lockfiles directly and looks up licenses via PyPI API.
- **Swift:** Parses `Package.resolved`, looks up licenses via GitHub API.
- **Kotlin:** Parses Gradle version catalogs (`libs.versions.toml`), looks up licenses via Maven Central.
- **Dart:** Parses `pubspec.lock` or `pubspec.yaml`, looks up via pub.dev API + GitHub.
- **Go:** Parses `go.sum`, maps module paths to GitHub repos for license lookup.
- **C#:** Parses `.csproj` or `Directory.Packages.props`, looks up licenses via NuGet API.
- **Solidity:** Parses `.gitmodules` for Foundry submodule deps + npm deps.

**Note:** The script outputs JSON to stdout and progress messages to stderr. Use `2>/dev/null` to capture clean JSON, or omit it to see progress.

### Step 2: Parse the JSON output and format the report

Read the JSON output from the script. If there's an `error` field, display it and stop.

### Step 3: Display the report

Format the results as a markdown report using this template:

```markdown
# License Compliance Report

**Project:** /path/to/project
**Package manager:** pnpm (monorepo, 24 workspaces)
**Scanned:** 1,847 packages in 3.2s
**Mode:** all dependencies

| Classification | Count | Status |
|:---------------|------:|:-------|
| Permissive     | 1,820 | OK     |
| Weak Copyleft  |     3 | MEDIUM |
| Restrictive    |     1 | HIGH   |
| Unknown        |    23 | Review |

## HIGH: Restrictive Licenses

| Package | Version | License | Dev? | Introduced By |
|:--------|:--------|:--------|:-----|:--------------|
| some-gpl-pkg | 2.1.0 | GPL-3.0 | No | `wasm-parser` added by Jane Doe on 2024-03-15 ([a1b2c3d](https://github.com/org/repo/commit/a1b2c3d)) |

> Strong copyleft obligations — likely incompatible with commercial use. These packages must be replaced or receive legal approval.
>
> **Introduced By** shows which direct dependency pulled in the violation, who added it, and when. If the flagged package is itself a direct dependency, just the author/date is shown. If blame data is unavailable (shallow clone, no git history), the column shows "—".

## MEDIUM: Weak Copyleft

| Package | Version | License | Dev? |
|:--------|:--------|:--------|:-----|
| some-mpl-pkg | 1.0.0 | MPL-2.0 | No |

> May be acceptable depending on linking/usage. Flag for review.

## Unknown Licenses (Manual Review)

| Package | Version | Raw License |
|:--------|:--------|:------------|
| mystery-pkg | 0.3.1 | SEE LICENSE IN LICENSE.md |

> These packages have non-standard or missing license declarations. Check their repos manually.

## Action Items

1. **Replace** restrictive-licensed packages or obtain legal approval
2. **Review** weak copyleft packages for linking compatibility
3. **Verify** unknown licenses by checking package repositories
```

Adapt the template based on actual results:
- Omit sections with zero entries (e.g., skip "HIGH" section if no restrictive packages)
- If everything is permissive and no unknowns, display a clean bill of health
- Note if `--prod-only` was used
- Include exit code info: exit 0 = clean, exit 2 = HIGH violations found

## Org-wide scanning workflow

Use this workflow when the user invokes `/license-compliance --org` or asks for an org-wide license sweep.

### Step 0: Locate or create tracker and report files

Before running the scanner, check if the user already has a tracker file and report:

1. **Search for existing tracker:** Look for `license-tracker.json` in the user's working directory and common locations. If found, confirm: "I found an existing tracker at `<path>` — should I use it?"
2. **If no tracker exists:** Ask the user where to store both files. Suggest placing them alongside related reports in the same directory.
3. **Always ask for report path too:** The script generates a markdown report via `--report`. Ask where to write it, or suggest `license-compliance-report.md` next to the tracker.

### Step 1: Run the org scanner

The script takes `--tracker` (JSON state file) and `--report` (markdown output) as separate paths.

First run (discovers + scans all supported repos):
```bash
python3 ~/.claude/skills/license-compliance/scripts/org_scanner.py \
  --orgs reown-com,walletconnect \
  --tracker <tracker-path>/license-tracker.json \
  --report <report-path>/license-compliance-report.md 2>/dev/null
```

Discovery only (no scanning, useful for initial setup):
```bash
python3 ~/.claude/skills/license-compliance/scripts/org_scanner.py \
  --orgs reown-com,walletconnect \
  --tracker <tracker-path>/license-tracker.json \
  --report <report-path>/license-compliance-report.md \
  --discover-only 2>/dev/null
```

Resume / re-scan stale repos:
```bash
python3 ~/.claude/skills/license-compliance/scripts/org_scanner.py \
  --orgs reown-com,walletconnect \
  --tracker <tracker-path>/license-tracker.json \
  --report <report-path>/license-compliance-report.md \
  --stale-days 30 2>/dev/null
```

Scan specific repos only:
```bash
python3 ~/.claude/skills/license-compliance/scripts/org_scanner.py \
  --tracker <tracker-path>/license-tracker.json \
  --report <report-path>/license-compliance-report.md \
  --only reown-com/appkit,reown-com/web-monorepo 2>/dev/null
```

**Resume behavior:** When the tracker file already exists and `--orgs` is provided, the scanner discovers new repos and merges them into the existing tracker. It only scans repos that haven't been scanned yet (or are stale per `--stale-days`). Already-scanned repos are skipped. The tracker saves after each repo scan, so interrupted runs resume from where they left off.

### Step 2: Display the report

The `--report` flag generates the markdown report automatically. Read and display it to the user. If `--report` was not used, format the JSON output into a similar report manually.

### Step 3: Handle long-running scans

Org-wide scans can take 30+ minutes for large orgs. The scanner:
- Saves the tracker after each repo scan (crash-safe resume)
- Reports progress to stderr
- Can be interrupted and resumed with the same command

If interrupted, re-running with the same args picks up where it left off.

## Exit codes

- `0` — No restrictive license violations
- `1` — Script error (missing lockfile, clone failure, etc.)
- `2` — HIGH severity violations found (restrictive licenses in dependencies)

## License tiers (source of truth)

### Permissive (OK)
MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, CC0-1.0, 0BSD, BlueOak-1.0.0, Zlib, Artistic-2.0, WTFPL, MIT-0, PSF-2.0, CC-BY-4.0, CC-BY-3.0, BSL-1.0, Unicode-3.0, Unicode-DFS-2016

### Restrictive (HIGH)
GPL-2.0/3.0 variants, AGPL-3.0 variants, SSPL-1.0, EUPL, OSL-3.0

### Weak Copyleft (MEDIUM)
LGPL-2.1/3.0 variants, MPL-2.0, EPL-1.0/2.0, CDDL-1.0/1.1

### Dev dependency reduction
Dev dependencies get severity reduced one level (HIGH→MEDIUM, MEDIUM→LOW).
