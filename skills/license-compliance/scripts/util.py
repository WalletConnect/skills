"""Shared utility functions."""

from __future__ import annotations

import subprocess
from typing import Optional


def run_command(args: list[str], cwd: Optional[str] = None, timeout: int = 300) -> tuple[bool, str]:
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, cwd=cwd, timeout=timeout
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or result.stdout.strip()
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s: {' '.join(args)}"
    except FileNotFoundError:
        return False, f"Command not found: {args[0]}"
