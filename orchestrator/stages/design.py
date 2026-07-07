"""Design stage: verifies a design/ADR artifact exists and is non-empty before
implementation is allowed to start."""
from __future__ import annotations

from pathlib import Path

from orchestrator.engine import RunContext, StageResult


def run(ctx: RunContext, params: dict) -> StageResult:
    artifact_path = Path(params["artifact"])
    if not artifact_path.is_absolute():
        artifact_path = ctx.repo_root / artifact_path

    if not artifact_path.exists():
        return StageResult(status="fail", notes=f"design artifact not found: {artifact_path}")

    text = artifact_path.read_text(encoding="utf-8")
    if not text.strip():
        return StageResult(status="fail", notes="design artifact is empty")

    ctx.set("design.artifact", str(artifact_path))
    return StageResult(status="pass", output={"artifact": str(artifact_path)},
                        notes="design artifact validated")
