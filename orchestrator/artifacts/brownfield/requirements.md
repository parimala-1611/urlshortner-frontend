# Requirements — Brownfield: CORS Configuration

## Raw input

"Add CORS configuration to the backend."

## Interpretation

A well-defined enhancement to an existing, already-documented gap: `docs/BACKEND.md`
and `docs/FRONTEND_INTEGRATION.md` both explicitly flag "no CORS configuration exists
yet" as a blocker for any frontend running on a different origin than the API
(e.g. Vite on `localhost:5173` calling the API on `localhost:8080`).

## Codebase reasoning (impacted areas)

- **No existing `WebMvcConfigurer` bean** — `src/main/java/com/urlshortener/` has no
  config package or CORS-related class today; this is a net-new addition, not a
  modification of existing config.
- **`application.yml`** — needs a new configurable property for allowed origins, so
  this isn't hardcoded per environment (dev vs. prod frontends will differ).
- **All controller endpoints** (`ShortUrlController`) are affected equally — CORS is
  cross-cutting (a global `WebMvcConfigurer`), not per-endpoint, so no controller code
  changes are needed.
- **Docs** — `docs/BACKEND.md` and `docs/FRONTEND_INTEGRATION.md` both contain
  now-stale "no CORS" warnings that must be corrected, not just supplemented, or the
  docs actively mislead the next reader.
- **No data flow / schema impact** — this is purely a cross-cutting web-layer concern;
  the database schema, service layer, and DTOs are untouched.

## Normalized engineering problem

Add a configurable CORS policy (allowed origins driven by an `application.yml`
property, not hardcoded) so a frontend on a different origin can call the API,
while defaulting to **no origins allowed** (secure by default) until an operator
explicitly configures one or more origins.

## Acceptance criteria

1. A request with an `Origin` header matching a configured allowed origin receives
   `Access-Control-Allow-Origin` in the response and the preflight (`OPTIONS`)
   succeeds.
2. A request with an `Origin` header that does NOT match any configured origin is
   rejected by Spring's CORS processing (no `Access-Control-Allow-Origin` header;
   preflight fails).
3. With no origins configured (the default), no origin is allowed — behavior is
   unchanged from before this change for anyone who hasn't opted in.
4. `docs/BACKEND.md` and `docs/FRONTEND_INTEGRATION.md` no longer claim "no CORS
   configuration exists" and instead explain how to configure it.
