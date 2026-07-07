"""Release-readiness stage: the final aggregate gate. Requires human approval
(enforced by the engine before this runner is even invoked, via
`requires_approval` on the stage) and, once approved, writes a release
manifest recording what is being released and the full decision context.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from orchestrator.engine import RunContext, StageResult


def run(ctx: RunContext, params: dict) -> StageResult:
    manifest = {
        "released_at": time.time(),
        "context": ctx.snapshot(),
    }
    out_path = Path(params["manifest_path"])
    if not out_path.is_absolute():
        out_path = ctx.repo_root / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return StageResult(status="pass", output={"manifest": str(out_path)}, notes="release manifest written")
