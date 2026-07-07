"""Implementation stage: verifies real code changes exist relative to the
pipeline's captured baseline git ref, optionally scoped to expected paths.
"""
from __future__ import annotations

import subprocess

from orchestrator.engine import RunContext, StageResult


def run(ctx: RunContext, params: dict) -> StageResult:
    base_ref = params["base_ref"]
    expected_path_prefixes: list[str] = params.get("expected_paths", [])

    result = subprocess.run(
        ["git", "diff", "--name-only", base_ref],
        cwd=ctx.repo_root, capture_output=True, text=True, check=False,
    )
    changed = [line for line in result.stdout.splitlines() if line.strip()]

    if not changed:
        return StageResult(status="fail", notes="no code changes detected since baseline")

    if expected_path_prefixes:
        matched = [f for f in changed if any(f.startswith(p) for p in expected_path_prefixes)]
        if not matched:
            return StageResult(
                status="fail",
                notes=f"changes exist but none match expected paths {expected_path_prefixes}: {changed}",
            )

    ctx.set("implementation.changed_files", changed)
    return StageResult(status="pass", output={"changed_files": changed}, notes=f"{len(changed)} files changed")
