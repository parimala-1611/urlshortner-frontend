"""Pipeline specification model: stages, dependencies, and gates.

A pipeline is loaded from a JSON spec (see orchestrator/pipelines/*.json).
Stage graph shape (deps, cycles) is validated at load time so a malformed
pipeline spec fails fast instead of hanging the engine later.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Stage:
    name: str
    runner: str  # dotted path to a callable, e.g. "orchestrator.stages.test.run"
    depends_on: list[str] = field(default_factory=list)
    max_retries: int = 0
    retry_backoff_seconds: float = 1.0
    requires_approval: bool = False
    rollback_on_failure: bool = False
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Pipeline:
    name: str
    description: str
    stages: list[Stage]

    def stage(self, name: str) -> Stage:
        for s in self.stages:
            if s.name == name:
                return s
        raise KeyError(f"Unknown stage: {name}")

    @classmethod
    def load(cls, path: str | Path) -> "Pipeline":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        stages = [Stage(**s) for s in data["stages"]]
        cls._validate_graph(stages)
        return cls(name=data["name"], description=data.get("description", ""), stages=stages)

    @staticmethod
    def _validate_graph(stages: list[Stage]) -> None:
        names = {s.name for s in stages}
        for s in stages:
            for dep in s.depends_on:
                if dep not in names:
                    raise ValueError(f"Stage '{s.name}' depends on unknown stage '{dep}'")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(n: str) -> None:
            if n in visited:
                return
            if n in visiting:
                raise ValueError(f"Cycle detected in pipeline graph at stage '{n}'")
            visiting.add(n)
            stage = next(s for s in stages if s.name == n)
            for dep in stage.depends_on:
                visit(dep)
            visiting.discard(n)
            visited.add(n)

        for s in stages:
            visit(s.name)
