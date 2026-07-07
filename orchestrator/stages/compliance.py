"""Compliance stage: runs the policy guardrail checks (secrets, protected
files, change-size bound) against the real diff since baseline."""
from __future__ import annotations

from orchestrator import guardrails
from orchestrator.engine import RunContext, StageResult


def run(ctx: RunContext, params: dict) -> StageResult:
    base_ref = params["base_ref"]
    checks = [
        guardrails.no_secrets_in_diff(ctx.repo_root, base_ref),
        guardrails.no_protected_files_touched(ctx.repo_root, base_ref, params.get("protected_files")),
        guardrails.change_size_within_bounds(ctx.repo_root, base_ref, params.get("max_files", 25)),
    ]
    failures = [msg for ok, msg in checks if not ok]
    if failures:
        return StageResult(status="fail", notes="; ".join(failures))
    return StageResult(status="pass", notes="; ".join(msg for _, msg in checks))
