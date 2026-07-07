# Setup Instructions

Two independent things to run: the URL shortener frontend (Vite/React/TypeScript), and
the orchestration engine (Python) that governs changes to it. This `orchestrator/` is
this repo's own copy — adapted from the same engine originally built for the backend
(`UrlShortner`) repo, with its stage runners rewired from Maven/Java to npm/Vitest. The
DAG scheduler, gates, retry/rollback/approval logic, audit log, and metrics
(`engine.py`, `pipeline.py`, `audit.py`, `metrics.py`) are unchanged — only
`orchestrator/stages/test.py` and `orchestrator/guardrails.py`'s default protected-file
list differ between the two copies. See
[`ORCHESTRATION_ARCHITECTURE.md`](./ORCHESTRATION_ARCHITECTURE.md) for how it works.

## 1. The frontend

### Prerequisites

- Node.js 18+ and npm
- The backend (`UrlShortner`) running on `http://localhost:8080` for real API calls —
  see that repo's own setup docs. Not required to run the frontend's own build/lint/test
  commands below.

### Run it locally

```bash
npm install
npm run dev
```

Vite's dev server proxies `/api/*` to `http://localhost:8080` (see `vite.config.ts`), so
the browser never makes a cross-origin request against the backend.

### Run the tests

```bash
npm test
```

Vitest + React Testing Library, jsdom environment (`vite.config.ts`'s `test` block,
`src/setupTests.ts`). No external services required — API calls are mocked at the
`src/api/client.ts` boundary in tests.

### Build and lint

```bash
npm run build   # tsc -b && vite build
npm run lint     # oxlint
```

## 2. The orchestration engine

### Prerequisites

- Python 3.9+, standard library only — **no `pip install` needed**.
- The frontend's prerequisites above (the `test` stage runner actually invokes
  `npm test`).

### Run a scenario end-to-end

From the repo root:

```bash
python orchestrator/run.py start --pipeline orchestrator/pipelines/frontend-custom-alias.json --run-id my-run
```

If a stage requires approval, the run halts and prints the exact resume command:

```bash
python orchestrator/run.py approve my-run <stage> --pipeline orchestrator/pipelines/frontend-custom-alias.json --approver "<your name>" --note "<why>"
```

Check status or metrics at any time:

```bash
python orchestrator/run.py status my-run
python orchestrator/run.py report my-run
python orchestrator/run.py report --all      # aggregate across every run
```

The pipelines already committed to this repo
(`orchestrator/pipelines/{frontend-custom-alias,frontend-link-details}.json`) reference
the requirements/design artifacts and expected file paths for the features already
built — running them again with a fresh `--run-id` will simply re-validate that
everything still passes (tests still green, docs still present, no new compliance
violations) against the current `HEAD`, since no `--base-ref` is required for a re-run
against the current state of the repo.

### Run the orchestrator's own test suite

```bash
python -m unittest discover -s orchestrator/tests -t .
```

19 tests, no external services required (a throwaway git repo is created per test that
needs one) — these exercise the engine's control-flow (gates, retry, rollback, replan,
approval) via fixture stages, independent of the real `test.py`/`npm test` integration.

## Repo layout at a glance

```
src/                     Vite/React/TypeScript frontend
docs/                    All narrative documentation (this file, architecture,
                         scenarios, schemas, testing/limitations, final summary)
orchestrator/            The orchestration engine (Python, stdlib only)
  pipelines/*.json       Pipeline specs, one per scenario
  artifacts/             Requirements/design write-ups + release manifests (tracked)
  runs/                  Per-run audit logs (generated, gitignored)
  tests/                 The engine's own unit test suite
```
