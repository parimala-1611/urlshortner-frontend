"""Test stage: really runs the frontend test suite via npm (Vitest) and gates
on the actual process exit code - not a simulated/narrative pass.
"""
from __future__ import annotations

import subprocess
import sys

from orchestrator.engine import RunContext, StageResult


def run(ctx: RunContext, params: dict) -> StageResult:
    test_filter = params.get("test_filter")
    is_windows = sys.platform.startswith("win")
    npm = "npm.cmd" if is_windows else "npm"
    cmd = [npm, "test"]
    if test_filter:
        cmd += ["--", test_filter]

    proc = subprocess.run(cmd, cwd=ctx.repo_root, capture_output=True, text=True, shell=is_windows)

    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-40:])
        return StageResult(status="fail", notes=f"npm test failed (exit {proc.returncode}):\n{tail}")

    ctx.set("test.exit_code", proc.returncode)
    return StageResult(status="pass", output={"exit_code": proc.returncode}, notes="tests passed")
