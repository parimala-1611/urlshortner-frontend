"""DAG execution engine: entry/exit gates, bounded retry, rollback, safe-stop,
human approval checkpoints, and dynamic re-planning over a Pipeline.

Design notes:
- Stages ready at the same time (all deps satisfied) execute concurrently in a
  ThreadPoolExecutor "batch"; the engine waits for the whole batch before
  computing the next ready set - this is the sequential+parallel synchronization
  model the assignment asks for, without needing a fully async scheduler.
- RunContext is a single shared, thread-safe object carrying cross-stage
  outputs/decisions forward (cross-stage lineage).
- A stage can request `replan_to` in its StageResult to reopen an earlier stage
  with updated context (dynamic re-planning / non-linear execution). Bounded to
  MAX_REPLANS_PER_STAGE per stage per run to guarantee termination.
- Approval-required stages halt the whole run (ApprovalRequired) rather than
  auto-continuing; resuming requires an explicit, audited `approve` call.
- Unrecoverable failures either roll back (git reset --hard to the stage's
  captured pre-execution SHA) or safe-stop the entire run, marking untouched
  downstream stages as skipped - no partial/silent continuation either way.
"""
from __future__ import annotations

import importlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from orchestrator.audit import AuditLog
from orchestrator.pipeline import Pipeline, Stage


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    status: str  # "pass" or "fail"
    output: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    replan_to: str | None = None


class RunContext:
    """Thread-safe shared state carried across stages (cross-stage lineage)."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self._data: dict[str, Any] = {}
        self._lock = Lock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def load_snapshot(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._data.update(data)


class ApprovalRequired(Exception):
    def __init__(self, stage: str):
        super().__init__(f"Stage '{stage}' requires human approval")
        self.stage = stage


class SafeStop(Exception):
    def __init__(self, stage: str, reason: str):
        super().__init__(f"Safe-stop triggered at stage '{stage}': {reason}")
        self.stage = stage
        self.reason = reason


class Engine:
    MAX_REPLANS_PER_STAGE = 1

    def __init__(self, pipeline: Pipeline, run_id: str, run_dir: Path, repo_root: Path,
                 approvals: set[str] | None = None, base_ref: str | None = None):
        self.pipeline = pipeline
        self.run_id = run_id
        self.run_dir = run_dir
        self.audit = AuditLog(run_dir)
        self.context = RunContext(repo_root)
        self.status: dict[str, StageStatus] = {s.name: StageStatus.PENDING for s in pipeline.stages}
        self.retries_used: dict[str, int] = {s.name: 0 for s in pipeline.stages}
        self.replans_used: dict[str, int] = {s.name: 0 for s in pipeline.stages}
        self.approvals: set[str] = approvals or set()
        self._lock = Lock()
        self.base_ref = base_ref or self._git_sha()

    # ---- persistence ----

    def _state_path(self) -> Path:
        return self.run_dir / "state.json"

    def save_state(self) -> None:
        state = {
            "run_id": self.run_id,
            "pipeline": self.pipeline.name,
            "status": {k: v.value for k, v in self.status.items()},
            "retries_used": self.retries_used,
            "replans_used": self.replans_used,
            "context": self.context.snapshot(),
            "approvals": sorted(self.approvals),
            "base_ref": self.base_ref,
        }
        self._state_path().write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    @classmethod
    def resume(cls, pipeline: Pipeline, run_id: str, run_dir: Path, repo_root: Path) -> "Engine":
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        eng = cls(pipeline, run_id, run_dir, repo_root, approvals=set(state.get("approvals", [])))
        eng.status = {k: StageStatus(v) for k, v in state["status"].items()}
        eng.retries_used = state.get("retries_used", eng.retries_used)
        eng.replans_used = state.get("replans_used", eng.replans_used)
        eng.base_ref = state.get("base_ref", eng.base_ref)
        eng.context.load_snapshot(state.get("context", {}))
        return eng

    # ---- gate helpers ----

    def _entry_gate_ready(self, stage: Stage) -> bool:
        return all(self.status[d] == StageStatus.PASSED for d in stage.depends_on)

    @staticmethod
    def _load_runner(dotted: str) -> Callable[[RunContext, dict], StageResult]:
        module_name, func_name = dotted.rsplit(".", 1)
        module = importlib.import_module(module_name)
        return getattr(module, func_name)

    # ---- execution ----

    def run(self) -> str:
        """Executes the pipeline until completion, a safe-stop, or an approval
        pause. Returns one of: 'completed', 'awaiting_approval', 'safe_stopped'."""
        try:
            while True:
                ready = [
                    s for s in self.pipeline.stages
                    if self.status[s.name] == StageStatus.PENDING and self._entry_gate_ready(s)
                ]
                if not ready:
                    break
                with ThreadPoolExecutor(max_workers=max(1, len(ready))) as pool:
                    futures = {pool.submit(self._execute_stage, s): s for s in ready}
                    for fut in as_completed(futures):
                        fut.result()
                self.save_state()

            unresolved = [s.name for s in self.pipeline.stages if self.status[s.name] == StageStatus.PENDING]
            for name in unresolved:
                self.status[name] = StageStatus.SKIPPED
                self.audit.record(self.run_id, name, "skipped", "upstream dependency never passed")
            if unresolved:
                self.save_state()

            self._write_summary(terminal="completed")
            return "completed"
        except ApprovalRequired as ar:
            self.save_state()
            (self.run_dir / "pending_approval.json").write_text(
                json.dumps({"stage": ar.stage, "run_id": self.run_id}, indent=2), encoding="utf-8")
            self._write_summary(terminal="awaiting_approval")
            return "awaiting_approval"
        except SafeStop as ss:
            for s in self.pipeline.stages:
                if self.status[s.name] == StageStatus.PENDING:
                    self.status[s.name] = StageStatus.SKIPPED
                    self.audit.record(self.run_id, s.name, "skipped", "safe-stop upstream")
            self.save_state()
            self._write_summary(terminal="safe_stopped", detail=ss.reason)
            return "safe_stopped"

    def _execute_stage(self, stage: Stage) -> None:
        with self._lock:
            if self.status[stage.name] != StageStatus.PENDING:
                return
            self.status[stage.name] = StageStatus.RUNNING

        if stage.requires_approval and stage.name not in self.approvals:
            self.audit.record(self.run_id, stage.name, "approval_requested")
            with self._lock:
                self.status[stage.name] = StageStatus.PENDING
            raise ApprovalRequired(stage.name)

        # "enter" marks the start of real execution, after any approval gate -
        # kept 1:1 with the eventual pass/fail event so metrics aren't skewed
        # by an approval pause-then-resume (which isn't a failure).
        self.audit.record(self.run_id, stage.name, "enter")
        if stage.requires_approval and stage.name in self.approvals:
            self.audit.record(self.run_id, stage.name, "approval_granted")

        pre_sha = self._git_sha()
        params = dict(stage.params)
        params.setdefault("base_ref", self.base_ref)

        attempt = 0
        start = time.time()
        while True:
            attempt += 1
            try:
                runner = self._load_runner(stage.runner)
                result: StageResult = runner(self.context, params)
            except Exception as exc:  # runner crashed - treat as a failed stage, not an engine crash
                result = StageResult(status="fail", notes=f"runner raised: {exc!r}")

            duration_ms = (time.time() - start) * 1000
            self.retries_used[stage.name] = attempt - 1

            if result.status == "pass":
                self.status[stage.name] = StageStatus.PASSED
                self.context.set(f"{stage.name}.output", result.output)
                self.context.set(f"{stage.name}.notes", result.notes)
                self.audit.record(self.run_id, stage.name, "pass", result.notes, duration_ms)
                if result.replan_to:
                    self._maybe_replan(stage, result.replan_to)
                return

            if attempt - 1 < stage.max_retries:
                self.audit.record(self.run_id, stage.name, "retry", result.notes, duration_ms)
                time.sleep(stage.retry_backoff_seconds)
                continue

            self.audit.record(self.run_id, stage.name, "fail", result.notes, duration_ms)
            self.status[stage.name] = StageStatus.FAILED
            if stage.rollback_on_failure and pre_sha:
                self._rollback(stage, pre_sha)
                raise SafeStop(stage.name, f"{stage.name} failed after rollback: {result.notes}")
            raise SafeStop(stage.name, f"{stage.name} failed: {result.notes}")

    def _maybe_replan(self, stage: Stage, replan_to: str) -> None:
        if self.replans_used[stage.name] >= self.MAX_REPLANS_PER_STAGE:
            self.audit.record(self.run_id, stage.name, "replan_skipped",
                               f"replan cap reached for target '{replan_to}'")
            return
        self.replans_used[stage.name] += 1
        self.audit.record(self.run_id, stage.name, "replan",
                           f"reopening '{replan_to}' with updated context")
        for name in self._downstream_closure(replan_to):
            self.status[name] = StageStatus.PENDING

    def _downstream_closure(self, start: str) -> set[str]:
        result = {start}
        changed = True
        while changed:
            changed = False
            for s in self.pipeline.stages:
                if s.name in result:
                    continue
                if any(dep in result for dep in s.depends_on):
                    result.add(s.name)
                    changed = True
        return result

    def _git_sha(self) -> str | None:
        try:
            out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.context.repo_root,
                                  capture_output=True, text=True, check=True)
            return out.stdout.strip()
        except Exception:
            return None

    def _rollback(self, stage: Stage, pre_sha: str) -> None:
        self.audit.record(self.run_id, stage.name, "rollback", f"resetting to {pre_sha}")
        subprocess.run(["git", "reset", "--hard", pre_sha], cwd=self.context.repo_root, check=False)

    def _write_summary(self, terminal: str, detail: str = "") -> None:
        lines = [f"# Run {self.run_id} ({self.pipeline.name})", "", f"Terminal status: **{terminal}**"]
        if detail:
            lines.append(f"Detail: {detail}")
        lines += ["", "| Stage | Status | Retries | Replans |", "|---|---|---|---|"]
        for s in self.pipeline.stages:
            lines.append(
                f"| {s.name} | {self.status[s.name].value} | {self.retries_used[s.name]} | "
                f"{self.replans_used[s.name]} |")
        (self.run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
