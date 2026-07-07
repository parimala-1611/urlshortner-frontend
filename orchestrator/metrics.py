"""Reliability metrics computed from one or more run audit logs: success rate,
retry/rollback frequency, MTTR, and end-to-end latency.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_events(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "audit.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_run_metrics(run_dir: Path) -> dict[str, Any]:
    events = _load_events(run_dir)
    if not events:
        return {"error": "no audit events found", "run_dir": str(run_dir)}

    stage_attempts: dict[str, int] = defaultdict(int)
    stage_passes: dict[str, int] = defaultdict(int)
    retries = 0
    rollbacks = 0
    replans = 0
    fail_times: dict[str, float] = {}
    recovery_durations: list[float] = []

    for ev in events:
        stage, kind, ts = ev["stage"], ev["event"], ev["ts"]
        if kind == "enter":
            stage_attempts[stage] += 1
        elif kind == "pass":
            stage_passes[stage] += 1
            if stage in fail_times:
                recovery_durations.append(ts - fail_times.pop(stage))
        elif kind == "fail":
            fail_times[stage] = ts
        elif kind == "retry":
            retries += 1
        elif kind == "rollback":
            rollbacks += 1
        elif kind == "replan":
            replans += 1

    total_attempts = sum(stage_attempts.values())
    total_passes = sum(stage_passes.values())
    success_rate = (total_passes / total_attempts) if total_attempts else 0.0
    mttr = (sum(recovery_durations) / len(recovery_durations)) if recovery_durations else None

    start_ts = min(e["ts"] for e in events)
    end_ts = max(e["ts"] for e in events)

    return {
        "run_dir": str(run_dir),
        "stages_attempted": total_attempts,
        "stages_passed": total_passes,
        "success_rate": round(success_rate, 4),
        "retry_count": retries,
        "rollback_count": rollbacks,
        "replan_count": replans,
        "mttr_seconds": round(mttr, 3) if mttr is not None else None,
        "end_to_end_latency_seconds": round(end_ts - start_ts, 3),
    }


def compute_aggregate_metrics(runs_dir: Path) -> dict[str, Any]:
    if not runs_dir.exists():
        return {"error": "runs directory does not exist"}

    per_run = []
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        m = compute_run_metrics(run_dir)
        if "error" not in m:
            per_run.append(m)

    if not per_run:
        return {"error": "no runs with audit data found"}

    def avg(key: str) -> float:
        vals = [r[key] for r in per_run if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    mttrs = [r["mttr_seconds"] for r in per_run if r["mttr_seconds"] is not None]

    return {
        "runs_analyzed": len(per_run),
        "overall_success_rate": avg("success_rate"),
        "total_retries": sum(r["retry_count"] for r in per_run),
        "total_rollbacks": sum(r["rollback_count"] for r in per_run),
        "total_replans": sum(r["replan_count"] for r in per_run),
        "avg_mttr_seconds": round(sum(mttrs) / len(mttrs), 3) if mttrs else None,
        "avg_end_to_end_latency_seconds": avg("end_to_end_latency_seconds"),
        "per_run": per_run,
    }
