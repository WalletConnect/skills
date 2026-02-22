"""Shared GitHub license lookup and URL parser."""

from __future__ import annotations

import json
import subprocess
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote as urlquote
from urllib.request import Request, urlopen


def extract_github_org_repo(url: str) -> Optional[tuple[str, str]]:
    """Extract (org, repo) from a GitHub URL."""
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    # Handle https://github.com/org/repo
    if "github.com/" in url:
        parts = url.split("github.com/", 1)[1].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    return None


def lookup_github_license(owner: str, repo: str) -> Optional[str]:
    """Look up a repo's license via GitHub API."""
    url = f"https://api.github.com/repos/{urlquote(owner, safe='')}/{urlquote(repo, safe='')}/license"
    headers = {"User-Agent": "license-check-scanner/1.0", "Accept": "application/vnd.github.v3+json"}
    # Try to get auth token from gh CLI for higher rate limits
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            headers["Authorization"] = f"Bearer {result.stdout.strip()}"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        spdx = data.get("license", {}).get("spdx_id", "")
        if spdx and spdx != "NOASSERTION":
            return spdx
    except (URLError, json.JSONDecodeError, OSError, KeyError):
        pass
    return None
