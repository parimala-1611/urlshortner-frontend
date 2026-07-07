# Agentic SDLC Orchestration Architecture

This document describes the orchestration layer in `orchestrator/` — a real, runnable
engine (not a diagram or a narrative) that governs how changes move through
requirements → design → implementation → test → docs → compliance → release, with
gates, retries, rollback, human approval checkpoints, audit logging, and reliability
metrics. See [`SCENARIOS.md`](./SCENARIOS.md) for the scenarios it was used to drive,
and [`SETUP.md`](./SETUP.md) to run it yourself.

This repo's `orchestrator/` is a copy of the engine originally built for the backend
(`UrlShortner`) repo. The scheduler/gate/audit/metrics core below is identical between
the two copies; only the mechanical stage runners that shell out to the project's real
build tooling differ — here, `orchestrator/stages/test.py` runs `npm test` (Vitest)
instead of `mvnw test`, and `orchestrator/guardrails.py`'s default protected-file list
drops `pom.xml` (not applicable to a repo with no Maven build).

## Why a real engine, not just documentation

The alternative — describing an orchestration *policy* in prose and treating this
session's own tool calls (task lists, questions asked) as an implicit "orchestrator" —
can't demonstrate that a gate actually blocks, a retry actually re-runs a failed step,
or a rollback actually restores prior state. The engine here does all three for real,
verified two ways: a dedicated unit test suite (`orchestrator/tests/`, 19 tests) that
exercises the control-flow in isolation, and three full scenario runs against this
repo's actual codebase with real `git`/`mvnw` commands and real audit logs.

## Components

```
orchestrator/
  pipeline.py       Stage/Pipeline data model. Loads a pipeline spec (JSON), validates
                     the dependency graph (unknown deps, cycles) at load time.
  engine.py         The scheduler. Everything described below lives here.
  audit.py          Append-only JSON-lines audit log per run + human-readable summary.
  metrics.py        Reads audit logs, computes success rate / retry & rollback
                     frequency / MTTR / end-to-end latency, per-run and aggregate.
  guardrails.py     Policy checks run against the real git diff: no secrets, no
                     unapproved protected-file changes, change-size bound.
  stages/           Generic, reusable stage runners (requirements, design,
                     implementation, test, docs, compliance, release_readiness) shared
                     by all three pipeline specs.
  pipelines/*.json  One spec per scenario: stage graph, dependencies, gates, retry/
                     rollback/approval policy per stage.
  artifacts/        Requirements/design write-ups (the "cognitive stage" outputs) and
                     release manifests - real source content, tracked in git.
  runs/             Per-run audit.jsonl + state.json + summary.md - generated output,
                     gitignored (see "A real bug this caught" below for why).
  run.py            CLI: start / approve / status / report.
```

## Orchestration model

### Dependency graph with entry/exit gates

A pipeline spec (JSON) declares stages with `depends_on`. A stage's **entry gate** is
simply "all declared dependencies passed" plus whatever preconditions its own runner
checks (e.g. the `implementation` stage's entry gate is implicit: it won't even be
scheduled until `design` has passed). Its **exit gate** is stage-specific and real:
the `test` stage's exit gate is "the actual `npm test` (Vitest) process exited 0"; the
`docs` stage's is "the actual `git diff` includes the expected doc files"; `compliance`'s
is "no guardrail check failed."

### Sequential and parallel execution with synchronization

The engine computes the set of stages whose dependencies are all satisfied and runs
that whole batch **concurrently** (`ThreadPoolExecutor`), then recomputes the next
batch once all of the current one finishes. In every pipeline used here, `test` and
`docs` both depend only on `implementation` and nothing on each other — they run in
parallel, and `compliance` (which depends on both) acts as the synchronization barrier
before release. This is real, observable concurrency: the "enter" timestamps for
`test` and `docs` in a run's `audit.jsonl` overlap.

### Cross-stage context and decision lineage

A single `RunContext` object is threaded through every stage: after a stage passes,
its `output` and `notes` are written into the context, and the whole context snapshot
is persisted to `state.json` after every stage. Later stages (and a human reviewing
`state.json`) can see exactly what an earlier stage decided and why, not just
pass/fail.

### Human approval checkpoints

A stage marked `requires_approval: true` halts the entire run the moment the engine
reaches it — it writes `pending_approval.json` and returns a non-zero exit code. There
is no way to proceed past it except an explicit, separately-audited
`python orchestrator/run.py approve <run_id> <stage> --approver <name> --note <reason>`
call. This isn't limited to a final release gate: the ambiguous scenario places this
checkpoint on the **requirements** stage itself, so a human signs off on the
*interpreted scope* of a vague request before any design or implementation work
happens (see `SCENARIOS.md`).

### Bounded retry, rollback, and safe-stop

- **Retry**: a stage can declare `max_retries`; on failure the engine retries with a
  configurable backoff, logging every attempt. Verified with a fixture stage that
  fails N times then passes (`orchestrator/tests/test_engine_retry.py`).
- **Rollback**: a stage captures the repo's git SHA before it runs; if it fails
  unrecoverably and is marked `rollback_on_failure`, the engine runs
  `git reset --hard <captured-sha>` and logs the rollback event. Verified against a
  *real* throwaway git repo, not a mock (`test_engine_rollback.py`).
- **Safe-stop**: any unrecoverable failure halts the *entire* run, marks every
  not-yet-started stage `skipped`, and writes a final summary — no partial or silent
  continuation.

### Dynamic re-planning

A stage's runner can return `replan_to: "<earlier-stage>"` in its result. The engine
reopens that stage (and everything downstream of it) to `pending` and re-traverses
forward with updated context — a genuine non-linear, stateful execution path, not a
strict top-to-bottom chain. Bounded to one replan per stage per run
(`MAX_REPLANS_PER_STAGE`) so it's guaranteed to terminate. Verified in
`test_engine_replan.py`.

### Policy guardrails

The `compliance` stage runs three checks against the real diff: no secret-shaped
strings, no touches to a configurable protected-files list (default:
`.github/workflows/`, `pom.xml`) without that pipeline explicitly opting in, and a
change-size bound. This actually fired for real during the greenfield run — adding the
ZXing dependency touched `pom.xml`, tripping the default guardrail — see
`SCENARIOS.md` for how that was resolved (per-pipeline configuration with a documented
rationale, not a global weakening of the check).

### Audit-grade observability and reliability metrics

Every stage transition is one JSON line in `runs/<id>/audit.jsonl`: timestamp, stage,
event (`enter`/`pass`/`fail`/`retry`/`rollback`/`replan`/`approval_requested`/
`approval_granted`/`skipped`), and detail. `metrics.py` reads this (one run or all
runs) to compute success rate, retry/rollback frequency, MTTR (mean time between a
stage's `fail` event and its later `pass`), and end-to-end latency — see
`orchestrator/artifacts/aggregate_metrics_report.json` for the real numbers across all
three scenario runs.

## Key design decisions

| Decision | Choice | Why |
|---|---|---|
| Language/runtime | Python, standard library only | Standalone from the Java build, zero install friction for evaluators (`python orchestrator/run.py ...`, no `pip install`). |
| Pipeline spec format | JSON, not YAML | Stdlib-only constraint - `json` is built in, a YAML parser isn't. |
| Cognitive stages (requirements/design/implementation) | Performed by the AI agent (me) in-session, submitted as artifacts the engine validates/gates | No LLM API is wired into the engine itself (see Limitations); the engine's job is to gate, log, retry, and require approval on this work exactly like it does for mechanical stages, not to generate it. |
| Mechanical stages (test/docs/compliance) | Genuinely automated via `subprocess` (`mvnw test`, `git diff`) | These are real, verifiable pass/fail signals - the whole point of the exercise is that the engine's gates are enforced, not asserted. |
| Approval mechanism | CLI halt + separate `approve` command | Real, auditable, out-of-band human action - no way to silently "auto-approve" mid-run. |
| Where run/audit output lives | `orchestrator/runs/`, gitignored | Generated output, not source - see "A real bug this caught" below. |
| Where requirements/design artifacts live | `orchestrator/artifacts/`, tracked in git | These are real authored content (the actual interpretation/design decisions), not disposable logs. |

## A real bug this caught (and fixed)

Early in building the rollback mechanism, a test scenario had the engine's own
`runs/` directory nested inside the same git repo a stage's `git add .` would commit.
The stage's commit swept up the engine's own audit file into the commit; the
subsequent `git reset --hard` rollback then correctly (from git's perspective) deleted
that file, since it wasn't part of the target commit. The fix was to gitignore the
run-output directory (`orchestrator/runs/`) so a product-code commit can never
accidentally capture the orchestrator's own bookkeeping — documented here because it's
a genuine, non-obvious risk of embedding an orchestrator's state inside the same repo
it's operating on, not a hypothetical one.
