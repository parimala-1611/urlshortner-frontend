# URL Shortener — Frontend

A React/TypeScript frontend for the [UrlShortner](https://github.com/parimala-1611/UrlShortner)
backend (Spring Boot/Java): shorten a URL (with an optional custom alias), look up its
stats, view its QR code, and view click analytics. No authentication — every page works
against a public, anonymous API.

This repo also carries its own copy of the SDLC orchestration engine originally built
for the backend — a real, runnable engine (not a diagram) that gated every feature in
this repo through requirements → design → implementation → test → docs → compliance →
release, with human-approval checkpoints. See [Orchestration](#sdlc-orchestration)
below.

## Features

| Page | What it does |
|---|---|
| **Shorten** (`/`) | Submit a URL, get back a short link. Optional custom alias (6-12 alphanumeric characters) and expiry. Validates the URL and alias client-side before calling the API, and tells you if your requested alias wasn't available and the backend substituted a different one. Keeps a local history of links you've created (`localStorage`). |
| **Stats** (`/stats/:shortCode`) | Look up a short code's metadata (original URL, created/expires timestamps, click count), its QR code, and its analytics (total clicks, a daily-clicks chart, top referrers) — each fetched independently, so one 404 doesn't hide the others. |

## Tech stack

- **React 19** + **TypeScript**, built with **Vite**
- **React Router** for the two-page navigation
- **Tailwind CSS 4** for styling (light/dark mode via `dark:` variants)
- **Vitest** + **React Testing Library** for tests
- **oxlint** for linting

## Getting started

### Prerequisites

- Node.js 18+ and npm
- The [backend](https://github.com/parimala-1611/UrlShortner) running on
  `http://localhost:8080` for real API calls (not required to run `npm test`, `npm run
  build`, or `npm run lint`)

### Install & run

```bash
npm install
npm run dev      # starts the dev server at http://localhost:5173
```

Vite's dev server proxies `/api/*` to `http://localhost:8080` (see `vite.config.ts`),
so the browser never makes a cross-origin request against the backend directly. To
point at a different backend URL (e.g. a deployed instance), set `VITE_API_BASE_URL`.

### Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Start the Vite dev server |
| `npm test` | Run the Vitest suite (jsdom, React Testing Library) |
| `npm run build` | Type-check (`tsc -b`) and build for production |
| `npm run lint` | Lint with oxlint |
| `npm run preview` | Preview the production build locally |

## Project structure

```
src/
  api/            client.ts (fetch wrapper) + types.ts (request/response shapes)
  components/     CopyButton, DailyClicksChart (analytics bar chart), Layout
  hooks/          useHistory (localStorage-backed link history)
  lib/            validation.ts (client-side URL/alias validation)
  pages/          ShortenPage, StatsPage
docs/             Narrative documentation (see below)
orchestrator/     SDLC orchestration engine (Python, stdlib only)
```

## Testing

```bash
npm test
```

Vitest + React Testing Library against jsdom. API calls are mocked at the
`src/api/client.ts` boundary (`vi.mock`, keeping the real `ApiError` class for
`instanceof` checks) — no backend or network access required. Covers: client-side
validation logic, form submission and error states, the custom-alias fallback notice,
and the stats/QR/analytics page's independent-fetch and graceful-degradation behavior.

## SDLC orchestration

`orchestrator/` is a real, runnable engine — not narrative documentation — that governs
how changes move through this repo: a DAG scheduler with entry/exit gates, bounded
retry, rollback (`git reset --hard` on unrecoverable failure), human-approval
checkpoints that halt a run until an explicit, audited `approve` command, an
append-only audit log, and reliability metrics. It was originally built for the
backend repo and adapted here to run against this repo's own tooling (`npm test`
instead of `mvnw test`).

Two real feature scenarios were driven through it in this repo — custom alias support
and the QR/analytics link-details view — each ending in a human-approved release. Full
details, including a real bug the engine itself caught and fixed mid-run, in:

- [`docs/SETUP.md`](docs/SETUP.md) — how to run the engine and its own test suite
- [`docs/ORCHESTRATION_ARCHITECTURE.md`](docs/ORCHESTRATION_ARCHITECTURE.md) — how it works
- [`docs/SCENARIOS.md`](docs/SCENARIOS.md) — the five scenarios (three backend, two frontend) it was used to drive
- [`docs/TESTING_AND_LIMITATIONS.md`](docs/TESTING_AND_LIMITATIONS.md) — testing approach and known limitations

## API reference

This frontend is built against the backend's documented contract:

- [`docs/apiflow.md`](docs/apiflow.md) — call-by-call flow (what happens in what order)
- [`docs/BACKEND.md`](docs/BACKEND.md) — feature behavior
- [`docs/schemas.md`](docs/schemas.md) — exact request/response shapes
- [`docs/FRONTEND_INTEGRATION.md`](docs/FRONTEND_INTEGRATION.md) — gotchas, CORS setup, what's implemented where

## Related repository

Backend (Spring Boot/Java): <https://github.com/parimala-1611/UrlShortner>
