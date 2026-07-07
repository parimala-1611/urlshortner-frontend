"""Shared test helpers: a throwaway git repo so rollback/guardrail tests exercise
real `git` subprocess calls instead of mocking them away."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def make_temp_git_repo() -> Path:
    """A throwaway repo with `_run/` gitignored up front - mirrors the real
    repo's `orchestrator/runs/` being gitignored, so a stage's `git add .`
    can never accidentally sweep the engine's own audit trail into a commit
    (and a later rollback can't delete it out from under the engine)."""
    tmp = Path(tempfile.mkdtemp(prefix="orch-test-repo-"))
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, check=True)
    (tmp / "README.md").write_text("initial\n", encoding="utf-8")
    (tmp / ".gitignore").write_text("_run/\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=tmp, check=True)
    return tmp
