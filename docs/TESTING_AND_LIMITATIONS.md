# Testing Approach, Limitations, and Trade-offs

## Testing approach

### Backend (Java)

TDD throughout: every feature in this repo (including all three scenarios) was built
test-first. Layers:

- **Unit tests** (Mockito) for pure logic: `UrlNormalizer`, `Base62Encoder`,
  `ShortCodeGenerator`, `ShortUrlService`, `AnalyticsService` (the day/referrer
  aggregation is tested as plain functions over in-memory `ClickEvent` objects — no
  database needed to verify grouping/sorting/limit-N is correct).
  `AnalyticsServiceTest`/`ShortUrlServiceTest`/`ShortUrlControllerTest` were extended,
  not replaced, when `resolve()`'s signature changed to record a referrer.
- **Slice tests** (`@WebMvcTest`) for controllers: `ShortUrlControllerTest`,
  `CorsConfigTest`/`CorsConfigDefaultTest` (the latter two send real `Origin`/preflight
  headers through MockMvc and assert on the real Spring CORS filter's response, not on
  "was a bean registered").
- **Integration tests** (Testcontainers Postgres, `@SpringBootTest`):
  `ShortUrlEndToEndTest`, `ShortUrlConcurrencyStressTest` (50 concurrent threads
  proving dedup and code generation stay correct under contention),
  `UrlShortenerApplicationTests`.

Current count: 80 tests outside the Testcontainers-dependent classes, all passing
locally; the Testcontainers-dependent tests compile and are designed to pass in CI
(see Limitations).

### Frontend (TypeScript)

Vitest + React Testing Library, added when this repo adopted the orchestration engine
(see `docs/SETUP.md`). 23 tests: pure-function coverage for `src/lib/validation.ts`,
component tests for `ShortenPage` (client-side validation blocks the API call; the
alias-fallback notice appears if and only if the returned `shortCode` differs from the
request) and `StatsPage` (QR image renders/fails gracefully; analytics 404s
independently of stats, per `docs/apiflow.md` Flow 3), and `DailyClicksChart`
(zero-fills gaps in `dailyClickCounts`). API calls are mocked at the
`src/api/client.ts` boundary (`vi.mock` with the real `ApiError` class preserved for
`instanceof` checks) rather than hitting a real backend — no Docker/Testcontainers
equivalent needed here since there's no database layer on this side.

### Orchestration engine (Python)

19 `unittest` tests in `orchestrator/tests/`, deliberately testing real control-flow,
not mocked-away behavior:

| Test file | What it proves |
|---|---|
| `test_pipeline.py` | Malformed pipeline specs (unknown dependency, a cycle) are rejected at load time, not discovered mid-run. |
| `test_engine_gates.py` | A dependent stage only starts after its dependency passes; independent stages both run; an upstream failure marks downstream stages `skipped`, not silently ignored. |
| `test_engine_retry.py` | A stage that fails twice then passes recovers within its retry budget (using a fixture that really fails N times, not a mock returning canned results); exhausting the retry budget safe-stops the run. |
| `test_engine_rollback.py` | Runs against a **real throwaway git repo**: a stage that commits a file then fails has that commit actually reverted by `git reset --hard`, verified by checking the real post-rollback SHA and that the file is gone. |
| `test_engine_approval.py` | An approval-required stage halts the run and writes `pending_approval.json`; resuming with the approval recorded completes it; a full pause-then-resume cycle doesn't skew the success-rate metric (a real bug this test suite caught and fixed). |
| `test_engine_replan.py` | A stage requesting `replan_to` reopens the target stage and everything downstream, re-executes them, and does not loop a second time (bounded re-planning). |
| `test_metrics.py` | Success rate / retry count / latency are computed correctly from a real run's audit log. |
| `test_guardrails.py` | Secret-pattern detection, protected-file detection, and change-size bounds are checked against a real git diff, not a mocked one. |

### Scenario-level "system tests"

The three pipelines (`orchestrator/pipelines/*.json`) were each actually run against
this repo via the CLI, producing real `orchestrator/runs/<id>/audit.jsonl` files that
are inspected in `SCENARIOS.md` — this is the closest equivalent to an end-to-end test
of the orchestration layer itself, since it exercises the real scheduler, real gates,
real `git`/`mvnw` subprocess calls, and (for the ambiguous scenario) two real
human-approval pause/resume cycles.

## A real bug this repo's scenarios caught (and fixed)

Running `frontend-custom-alias-1` for real (not narrative) surfaced a genuine gap in
the engine itself, inherited unnoticed from the backend copy: `git diff <base_ref>`
only compares paths already present in the index, so a file that was never `git
add`-ed at all — a brand-new file, exactly what the `implementation` stage most needs
to see — was invisible to every git-diff-based gate (`implementation`, `docs`,
`compliance`). The 19-test `orchestrator/tests/` suite didn't catch this because its
fixtures exercise control-flow, not real multi-file feature diffs. Fixed with `git add
-N` (intent-to-add) at engine start (`orchestrator/engine.py`); see `SCENARIOS.md`
section 4 for the full before/after. Worth calling out here specifically because it's
the same class of finding as the backend's rollback/`JAVA_HOME` bugs — a real defect
that only running the engine against a real change, rather than reasoning about it,
would surface.

## Known limitations

- **No live LLM-in-the-loop for cognitive stages.** The `requirements`/`design`
  stages validate that an artifact exists and meets shape requirements (e.g. an
  `## Assumptions` section when flagged ambiguous) — they don't themselves call an
  LLM to *generate* that content. In this project, I (the AI agent) authored those
  artifacts interactively and submitted them for the engine to gate, which is an
  honest reflection of how this was actually built, but a fully autonomous version
  would need to wire an actual model call into those stage runners.
- **Single-machine, sequential-batch execution.** Parallelism is real (concurrent
  `ThreadPoolExecutor` batches) but there's no distributed execution, no queue, no
  multi-node coordination. Fine for this scale; would need rearchitecting for a
  large multi-team pipeline.
- **CLI-based approval, not a UI.** `pending_approval.json` plus a documented CLI
  command is a real, auditable gate, but a production system would likely want a
  web UI or ChatOps integration for approvals rather than requiring shell access.
- **Bounded re-planning depth is fixed at 1.** `MAX_REPLANS_PER_STAGE = 1` guarantees
  termination but means a stage that would need a second round of upstream rework
  within the same run instead safe-stops. Chosen deliberately over an unbounded loop
  (which risks never terminating) — revisit if a real scenario needs more than one
  round-trip.
- **Retention/growth of `click_events`.** The ambiguous scenario's analytics feature
  logs one row per redirect with no purge policy analogous to the existing
  `short_urls` expiry/purge job — flagged in `orchestrator/artifacts/ambiguous/design.md`
  as a deliberate, documented deferral, not an oversight.
- **In-memory analytics aggregation cost.** `AnalyticsService` fetches all raw
  `click_events` rows for a short code and aggregates in Java, chosen specifically so
  the aggregation logic is unit-testable without a database. This trades away
  scalability for a very high-traffic short code; also documented as a deliberate,
  known trade-off in `design.md`, not a silent gap.
- **Local Testcontainers execution is broken on this development machine**
  (`docker exec` and `docker version` work, but Testcontainers 1.20.4's bundled
  docker-java client fails API version negotiation against this specific Docker
  Desktop build). This blocks running `ShortUrlEndToEndTest`,
  `ShortUrlConcurrencyStressTest`, and `UrlShortenerApplicationTests` locally. These
  tests compile cleanly and are designed to pass on CI (`ubuntu-latest` runners,
  which have a compatible Docker setup) — this is a documented local-environment
  quirk, not a defect in the tests or the app.
- **The three pipeline specs are demonstration-specific**, referencing exact expected
  file paths for the features already built. They're re-runnable (see
  [`SETUP.md`](./SETUP.md)) as a regression check against the current repo state, but
  a production version of this system would generate or template pipeline specs per
  change rather than hand-authoring one JSON file per feature.

## Trade-offs made deliberately (not overlooked)

- JSON pipeline specs instead of YAML — a direct consequence of the stdlib-only
  constraint, not a preference; JSON is less pleasant to hand-author but requires no
  dependency.
- Java-side analytics aggregation instead of SQL `GROUP BY`/`date_trunc` — testability
  over raw query efficiency, explicitly reasoned through in `design.md`.
- Secure-by-default CORS (empty origins list) instead of a permissive default — a
  frontend developer has to take one explicit configuration step, in exchange for the
  API never being silently open to arbitrary origins.
