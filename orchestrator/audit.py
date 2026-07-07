"""Structured, append-only audit logging for a pipeline run.

Every stage transition (enter/pass/fail/retry/rollback/replan/approval/skip)
is appended as one JSON line. This is the audit-grade observability trail:
nothing is summarized or lossy at write time, so `metrics.py` and human
reviewers can reconstruct exactly what happened and when.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass
class AuditEvent:
    ts: float
    run_id: str
    stage: str
    event: str
    detail: str = ""
    duration_ms: float | None = None


class AuditLog:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.run_dir / "audit.jsonl"
        self._lock = Lock()

    def record(self, run_id: str, stage: str, event: str, detail: str = "",
               duration_ms: float | None = None) -> None:
        ev = AuditEvent(ts=time.time(), run_id=run_id, stage=stage, event=event,
                         detail=detail, duration_ms=duration_ms)
        line = json.dumps(asdict(ev))
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def read_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
