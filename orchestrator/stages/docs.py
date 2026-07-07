"""Docs stage: verifies the expected documentation files were actually modified
relative to the pipeline's captured baseline git ref."""
from __future__ import annotations

import subprocess

from orchestrator.engine import RunContext, StageResult


def run(ctx: RunContext, params: dict) -> StageResult:
    base_ref = params["base_ref"]
    expected_docs: list[str] = params.get("expected_docs", [])

    result = subprocess.run(
        ["git", "diff", "--name-only", base_ref],
        cwd=ctx.repo_root, capture_output=True, text=True, check=False,
    )
    changed = [line for line in result.stdout.splitlines() if line.strip()]

    missing = [d for d in expected_docs if d not in changed]
    if missing:
        return StageResult(status="fail", notes=f"expected doc updates missing: {missing}")

    ctx.set("docs.changed_files", changed)
    return StageResult(status="pass", output={"changed_files": changed}, notes="doc updates verified")
