"""Requirements stage: verifies a requirements artifact exists and, for inputs
flagged ambiguous, that it explicitly documents assumptions before the
pipeline is allowed to proceed toward design/implementation.
"""
from __future__ import annotations

from pathlib import Path

from orchestrator.engine import RunContext, StageResult


def run(ctx: RunContext, params: dict) -> StageResult:
    artifact_path = Path(params["artifact"])
    if not artifact_path.is_absolute():
        artifact_path = ctx.repo_root / artifact_path

    if not artifact_path.exists():
        return StageResult(status="fail", notes=f"requirements artifact not found: {artifact_path}")

    text = artifact_path.read_text(encoding="utf-8")
    if not text.strip():
        return StageResult(status="fail", notes="requirements artifact is empty")

    if params.get("ambiguous") and "## Assumptions" not in text:
        return StageResult(
            status="fail",
            notes="input flagged ambiguous but artifact has no '## Assumptions' section",
        )

    ctx.set("requirements.artifact", str(artifact_path))
    return StageResult(status="pass", output={"artifact": str(artifact_path)},
                        notes="requirements artifact validated")
