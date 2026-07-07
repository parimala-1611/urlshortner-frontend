"""Policy guardrails: security/compliance/change-control checks run against the
real git diff before a change is allowed to proceed toward release. These are
deterministic, enforced checks (not narrative) - each returns (ok, message).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][a-z0-9]{16,}"),
    re.compile(r"(?i)password\s*[:=]\s*['\"].+['\"]"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----"),
    re.compile(r"(?i)secret\s*[:=]\s*['\"][a-z0-9]{16,}"),
]

DEFAULT_PROTECTED_FILES = [".github/workflows/"]


def _diff_text(repo_root: Path, base_ref: str) -> str:
    result = subprocess.run(
        ["git", "diff", base_ref, "--", "."],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )
    return result.stdout


def _diff_stat(repo_root: Path, base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", base_ref],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def no_secrets_in_diff(repo_root: Path, base_ref: str) -> tuple[bool, str]:
    diff = _diff_text(repo_root, base_ref)
    for pattern in SECRET_PATTERNS:
        if pattern.search(diff):
            return False, f"potential secret matched pattern: {pattern.pattern}"
    return True, "no secret patterns detected"


def no_protected_files_touched(repo_root: Path, base_ref: str,
                                protected: list[str] | None = None) -> tuple[bool, str]:
    protected = protected if protected is not None else DEFAULT_PROTECTED_FILES
    files = _diff_stat(repo_root, base_ref)
    hits = [f for f in files if any(f.startswith(p) for p in protected)]
    if hits:
        return False, f"protected files touched without explicit approval: {hits}"
    return True, "no protected files touched"


def change_size_within_bounds(repo_root: Path, base_ref: str, max_files: int = 25) -> tuple[bool, str]:
    files = _diff_stat(repo_root, base_ref)
    if len(files) > max_files:
        return False, f"change touches {len(files)} files, exceeds bound of {max_files}"
    return True, f"change touches {len(files)} files, within bound of {max_files}"
