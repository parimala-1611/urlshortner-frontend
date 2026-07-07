"""Stage runner fixtures used only by orchestrator/tests/*.

These simulate stage behaviors (pass/fail/flaky/replan/commit-then-fail) via
plain module-level state so engine control-flow (retry, rollback, approval,
replanning) can be exercised deterministically without touching real
git/mvnw work for the actual product.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from orchestrator.engine import RunContext, StageResult

_flaky_counters: dict[str, int] = {}
_replan_done: dict[str, bool] = {}


def always_pass(ctx: RunContext, params: dict) -> StageResult:
    return StageResult(status="pass", output={"ran": True}, notes="ok")


def always_fail(ctx: RunContext, params: dict) -> StageResult:
    return StageResult(status="fail", notes="deliberate failure")


def commit_then_fail(ctx: RunContext, params: dict) -> StageResult:
    repo = ctx.repo_root
    (Path(repo) / "unwanted.txt").write_text("bad\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "unwanted change"], cwd=repo, check=True)
    return StageResult(status="fail", notes="commit made but stage still fails validation")


def flaky_then_pass(ctx: RunContext, params: dict) -> StageResult:
    key = params["key"]
    fail_times = params.get("fail_times", 2)
    count = _flaky_counters.get(key, 0)
    _flaky_counters[key] = count + 1
    if count < fail_times:
        return StageResult(status="fail", notes=f"attempt {count + 1} deliberately failing")
    return StageResult(status="pass", notes=f"succeeded on attempt {count + 1}")


def replan_once_then_pass(ctx: RunContext, params: dict) -> StageResult:
    key = params["key"]
    target = params["replan_to"]
    if not _replan_done.get(key):
        _replan_done[key] = True
        return StageResult(status="pass", notes="requesting replan", replan_to=target)
    return StageResult(status="pass", notes="second pass, no replan")


def reset_fixture_state() -> None:
    _flaky_counters.clear()
    _replan_done.clear()
