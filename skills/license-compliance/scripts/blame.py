"""Git blame/tracer for violation provenance."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

from util import run_command


def _get_manifest_pathspecs(pm: str) -> list[str]:
    """Get git pathspec patterns for manifest files by package manager."""
    if pm in ("pnpm", "npm", "yarn"):
        return [":(glob)**/package.json"]
    elif pm == "cargo":
        return [":(glob)**/Cargo.toml"]
    elif pm in ("poetry", "uv"):
        return ["pyproject.toml"]
    elif pm == "pipenv":
        return ["Pipfile"]
    elif pm == "pip":
        return ["requirements.txt"]
    return []


def _find_direct_dep_in_manifest(project_path: Path, pm: str, pkg_name: str) -> bool:
    """Check if pkg_name is listed as a direct dependency in a manifest file."""
    import glob as globmod

    if pm in ("pnpm", "npm", "yarn"):
        for p in globmod.glob(str(project_path / "**" / "package.json"), recursive=True):
            if "node_modules" in p:
                continue
            try:
                with open(p) as f:
                    data = json.load(f)
                all_deps = {}
                all_deps.update(data.get("dependencies", {}))
                all_deps.update(data.get("devDependencies", {}))
                if pkg_name in all_deps:
                    return True
            except (json.JSONDecodeError, OSError):
                pass
    elif pm == "cargo":
        for p in globmod.glob(str(project_path / "**" / "Cargo.toml"), recursive=True):
            try:
                content = Path(p).read_text()
                in_deps = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if re.match(r'\[(dev-)?dependencies\]', stripped):
                        in_deps = True
                        continue
                    if stripped.startswith("["):
                        if f".{pkg_name}]" in stripped:
                            return True
                        in_deps = False
                        continue
                    if in_deps and re.match(rf'^{re.escape(pkg_name)}\s*=', stripped):
                        return True
            except OSError:
                pass
    elif pm in ("poetry", "uv"):
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                for line in content.splitlines():
                    stripped = line.strip()
                    if re.match(rf'^{re.escape(pkg_name)}\s*=', stripped, re.IGNORECASE):
                        return True
                if re.search(rf'["\']({re.escape(pkg_name)})[>=<~!\s\'"]', content, re.IGNORECASE):
                    return True
            except OSError:
                pass
    elif pm == "pipenv":
        pipfile = project_path / "Pipfile"
        if pipfile.exists():
            try:
                for line in pipfile.read_text().splitlines():
                    if re.match(rf'^{re.escape(pkg_name)}\s*=', line.strip(), re.IGNORECASE):
                        return True
            except OSError:
                pass
    elif pm == "pip":
        req = project_path / "requirements.txt"
        if req.exists():
            try:
                for line in req.read_text().splitlines():
                    stripped = line.strip()
                    if stripped and stripped.split("==")[0].split(">=")[0].split("[")[0].strip().lower() == pkg_name.lower():
                        return True
            except OSError:
                pass
    return False


def _trace_dep_chain_via_pm(
    project_path: Path, pm: str, pkg_name: str, verbose: bool
) -> tuple[str, list[str]]:
    """Use PM-specific command to trace dependency chain back to the direct dep.

    Returns (direct_dep_name, dependency_chain_list).
    """
    if pm in ("pnpm", "npm", "yarn"):
        # Try pnpm/npm/yarn specific commands first
        if pm == "pnpm":
            # Try without -r first, then with -r for monorepos
            ok, output = run_command(
                ["pnpm", "why", pkg_name], cwd=str(project_path), timeout=30
            )
            # empty output = package not found at root level, try recursive
            if not output:
                ok, output = run_command(
                    ["pnpm", "why", "-r", pkg_name], cwd=str(project_path), timeout=60
                )
                if not ok and verbose:
                    print(f"    pnpm why -r failed: {output[:200]}", file=sys.stderr)
            if ok and output:
                chain_names = []
                for line in output.splitlines():
                    cleaned = re.sub(r'^[\s\u2502\u251c\u2514\u2500\u252c\u2524]+', '', line).strip()
                    if not cleaned or cleaned.startswith("Legend:") or cleaned.endswith(":"):
                        continue
                    m = re.match(
                        r'^(@[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+|[a-zA-Z][a-zA-Z0-9_.-]*)[\s@](\d[\d.]*)',
                        cleaned,
                    )
                    if m:
                        chain_names.append(m.group(1))
                # chain_names[0] is the project/workspace name, skip it
                deps = [n for n in chain_names[1:] if n != pkg_name]
                if deps:
                    return deps[0], deps + [pkg_name]
                if pkg_name in chain_names:
                    return pkg_name, [pkg_name]

        elif pm == "npm":
            ok, output = run_command(
                ["npm", "ls", pkg_name, "--json"], cwd=str(project_path), timeout=30
            )
            if not ok and verbose:
                print(f"    npm ls failed: {output[:200]}", file=sys.stderr)
            if ok and output:
                try:
                    data = json.loads(output)

                    def _find_path(node: dict, target: str, path: list[str] | None = None) -> list[str] | None:
                        if path is None:
                            path = []
                        for name, info in node.get("dependencies", {}).items():
                            current = path + [name]
                            if name == target:
                                return current
                            found = _find_path(info, target, current)
                            if found:
                                return found
                        return None

                    chain = _find_path(data, pkg_name)
                    if chain and len(chain) >= 1:
                        return chain[0], chain
                except json.JSONDecodeError:
                    pass

        elif pm == "yarn":
            ok, output = run_command(
                ["yarn", "why", pkg_name], cwd=str(project_path), timeout=30
            )
            if not ok and verbose:
                print(f"    yarn why failed: {output[:200]}", file=sys.stderr)
            if ok and output:
                for line in output.splitlines():
                    match = re.search(r'"([^"]+)"\s+depends on it', line)
                    if match:
                        parent = match.group(1)
                        return parent, [parent, pkg_name]

        # Fallback for all JS PMs: search lockfile for dependency relationship
        if verbose:
            print(f"    Falling back to lockfile search...", file=sys.stderr)
        # Try pnpm-lock.yaml: search for which package depends on the target
        lockfile = project_path / "pnpm-lock.yaml"
        if pm == "pnpm" and lockfile.exists():
            try:
                content = lockfile.read_text()
                # In pnpm-lock.yaml, dependency entries look like:
                #   /pkg@version: or 'pkg@version': (root-level, indented by 2+)
                #     dependencies:
                #       target-pkg: version
                # We search for lines referencing our target as a dependency value
                lines = content.splitlines()
                current_pkg = None
                for line in lines:
                    # Detect package header lines (vary by lockfile version)
                    # v6+: '/pkg@version':  or  pkg@version:
                    # v9:  'pkg@version':
                    stripped = line.strip()
                    if not line.startswith("    ") and ("@" in stripped or stripped.endswith(":")):
                        header_match = re.match(
                            r"""[/'"]?(@[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+|[a-zA-Z][a-zA-Z0-9._-]*)@""",
                            stripped.lstrip("/"),
                        )
                        if header_match:
                            current_pkg = header_match.group(1)
                    # Check if this line declares the target as a dependency
                    if current_pkg and current_pkg != pkg_name:
                        dep_match = re.match(
                            rf'^\s+{re.escape(pkg_name)}:\s', line
                        )
                        if dep_match:
                            if verbose:
                                print(f"    Found in lockfile: {current_pkg} -> {pkg_name}", file=sys.stderr)
                            return current_pkg, [current_pkg, pkg_name]
            except OSError:
                pass
        # npm/yarn fallback: check nested node_modules
        elif root_pkg_path := (project_path / "package.json"):
            if root_pkg_path.exists():
                try:
                    with open(root_pkg_path) as f:
                        pkg_data = json.load(f)
                    all_direct = {}
                    all_direct.update(pkg_data.get("dependencies", {}))
                    all_direct.update(pkg_data.get("devDependencies", {}))
                    for direct_name in all_direct:
                        nested = project_path / "node_modules" / direct_name / "node_modules" / pkg_name
                        if nested.exists():
                            return direct_name, [direct_name, pkg_name]
                except (json.JSONDecodeError, OSError):
                    pass

    elif pm == "cargo":
        ok, output = run_command(
            ["cargo", "tree", "--invert", "-p", pkg_name, "--depth", "10"],
            cwd=str(project_path), timeout=60,
        )
        if ok and output:
            # Reverse dep tree: first line is pkg itself, last root-level entry
            # is a workspace member. We want the dep just before the workspace member.
            lines = output.strip().splitlines()
            chain = []
            for line in lines:
                name_match = re.match(r'^[\u2502\u251c\u2514\u2500 ]*([a-zA-Z][a-zA-Z0-9_-]*)', line)
                if name_match:
                    chain.append(name_match.group(1))
            if len(chain) > 1:
                # chain[0] = target pkg, chain[-1] = workspace root
                # Direct dep is chain[-2] if it exists, else chain[-1]
                direct = chain[-1]
                return direct, list(reversed(chain))

    # Python or fallback: mark as transitive with unknown direct parent
    return pkg_name, [pkg_name]


def _git_pickaxe(project_path: Path, dep_name: str, pathspecs: list[str]) -> Optional[dict]:
    """Use git log -S (pickaxe) to find the commit that introduced a dependency."""
    cmd = [
        "git", "log", "-S", dep_name,
        "--format=%H|%an|%ai|%s", "--",
    ] + pathspecs

    ok, output = run_command(cmd, cwd=str(project_path), timeout=15)
    if ok and output:
        lines = output.strip().splitlines()
        if lines:
            # Last line = oldest commit that changed the string count = first introduction
            line = lines[-1]
            parts = line.split("|", 3)
            if len(parts) >= 4:
                return {
                    "commit": parts[0][:7],
                    "author": parts[1],
                    "date": parts[2].split()[0],
                    "message": parts[3],
                }
    return None


def trace_blame_for_violations(
    project_path: Path, pm: str, violations: list[dict], verbose: bool
) -> list[dict]:
    """Enrich HIGH violations with git blame info tracing who added the dependency."""
    if not violations:
        return violations

    # Unshallow if needed for full history
    shallow_file = project_path / ".git" / "shallow"
    if shallow_file.exists():
        if verbose:
            print("  Unshallowing clone for git blame...", file=sys.stderr)
        ok, msg = run_command(
            ["git", "fetch", "--unshallow"], cwd=str(project_path), timeout=120
        )
        if not ok and verbose:
            print(f"  Warning: failed to unshallow: {msg}", file=sys.stderr)

    pathspecs = _get_manifest_pathspecs(pm)
    if not pathspecs:
        for v in violations:
            v["introduced_by"] = None
        return violations

    for violation in violations:
        pkg_name = violation["name"]
        if verbose:
            print(f"  Tracing blame for {pkg_name}...", file=sys.stderr)

        try:
            # Check if the flagged package is itself a direct dependency
            is_direct = _find_direct_dep_in_manifest(project_path, pm, pkg_name)
            if is_direct:
                direct_dep = pkg_name
                chain = [pkg_name]
                if verbose:
                    print(f"    {pkg_name} is a direct dependency", file=sys.stderr)
            else:
                # Trace the dependency chain via PM-specific command
                direct_dep, chain = _trace_dep_chain_via_pm(
                    project_path, pm, pkg_name, verbose
                )
                if verbose:
                    print(f"    Chain: {' -> '.join(chain)}", file=sys.stderr)
                    print(f"    Direct dep to blame: {direct_dep}", file=sys.stderr)

            # Git pickaxe: find the commit that introduced the direct dep
            blame = _git_pickaxe(project_path, direct_dep, pathspecs)
            if verbose:
                if blame:
                    print(f"    Blame: {blame['author']} on {blame['date']} ({blame['commit']})", file=sys.stderr)
                else:
                    print(f"    Blame: not found via git log -S", file=sys.stderr)

            if blame:
                violation["introduced_by"] = {
                    "direct_dependency": direct_dep,
                    "dependency_chain": chain,
                    **blame,
                }
            else:
                violation["introduced_by"] = None
        except Exception:
            violation["introduced_by"] = None

    return violations
