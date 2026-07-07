#!/usr/bin/env python3
"""CLI entrypoint for the orchestrator.

Usage:
    python orchestrator/run.py start --pipeline orchestrator/pipelines/greenfield.json
    python orchestrator/run.py approve <run_id> <stage> --pipeline <path> --approver <name> --note <reason>
    python orchestrator/run.py status <run_id>
    python orchestrator/run.py report <run_id>
    python orchestrator/run.py report --all
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.engine import Engine  # noqa: E402
from orchestrator.pipeline import Pipeline  # noqa: E402
from orchestrator import metrics as metrics_mod  # noqa: E402

ORCH_ROOT = Path(__file__).resolve().parent
REPO_ROOT = ORCH_ROOT.parent
RUNS_ROOT = ORCH_ROOT / "runs"


def _print_next_step(run_id: str, run_dir: Path) -> None:
    pending = json.loads((run_dir / "pending_approval.json").read_text(encoding="utf-8"))
    print(f"Approval required for stage '{pending['stage']}'. Resume with:")
    print(f"  python orchestrator/run.py approve {run_id} {pending['stage']} "
          f"--pipeline <pipeline.json> --approver <name> --note <reason>")


def cmd_start(args: argparse.Namespace) -> int:
    pipeline = Pipeline.load(args.pipeline)
    run_id = args.run_id or f"{pipeline.name}-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    run_dir = RUNS_ROOT / run_id
    engine = Engine(pipeline, run_id, run_dir, REPO_ROOT, base_ref=args.base_ref)
    terminal = engine.run()
    print(f"run_id={run_id} terminal={terminal}")
    if terminal == "awaiting_approval":
        _print_next_step(run_id, run_dir)
        return 2
    return 0 if terminal == "completed" else 1


def cmd_approve(args: argparse.Namespace) -> int:
    run_dir = RUNS_ROOT / args.run_id
    pending_path = run_dir / "pending_approval.json"
    if not pending_path.exists():
        print(f"No pending approval found for run '{args.run_id}'")
        return 1
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    if pending["stage"] != args.stage:
        print(f"Pending approval is for stage '{pending['stage']}', not '{args.stage}'")
        return 1

    pipeline = Pipeline.load(args.pipeline)
    engine = Engine.resume(pipeline, args.run_id, run_dir, REPO_ROOT)
    engine.approvals.add(args.stage)
    pending_path.unlink()

    terminal = engine.run()
    print(f"run_id={args.run_id} terminal={terminal}")
    if terminal == "awaiting_approval":
        _print_next_step(args.run_id, run_dir)
        return 2
    return 0 if terminal == "completed" else 1


def cmd_status(args: argparse.Namespace) -> int:
    run_dir = RUNS_ROOT / args.run_id
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    print(json.dumps(state["status"], indent=2))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    if args.all:
        report = metrics_mod.compute_aggregate_metrics(RUNS_ROOT)
    else:
        if not args.run_id:
            print("report requires a run_id, or pass --all")
            return 1
        report = metrics_mod.compute_run_metrics(RUNS_ROOT / args.run_id)
    print(json.dumps(report, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Start a new pipeline run")
    p_start.add_argument("--pipeline", required=True)
    p_start.add_argument("--run-id", dest="run_id", default=None)
    p_start.add_argument("--base-ref", dest="base_ref", default=None,
                          help="Git ref/SHA to diff against for implementation/docs/compliance "
                               "gates. Defaults to current HEAD if omitted.")
    p_start.set_defaults(func=cmd_start)

    p_approve = sub.add_parser("approve", help="Approve a paused stage and resume the run")
    p_approve.add_argument("run_id")
    p_approve.add_argument("stage")
    p_approve.add_argument("--pipeline", required=True)
    p_approve.add_argument("--approver", required=True)
    p_approve.add_argument("--note", default="")
    p_approve.set_defaults(func=cmd_approve)

    p_status = sub.add_parser("status", help="Show current stage status for a run")
    p_status.add_argument("run_id")
    p_status.set_defaults(func=cmd_status)

    p_report = sub.add_parser("report", help="Print reliability metrics for a run or all runs")
    p_report.add_argument("run_id", nargs="?")
    p_report.add_argument("--all", action="store_true")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
