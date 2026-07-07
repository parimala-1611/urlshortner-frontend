# URL Shortener — Backend Overview

Spring Boot 3.3.5 / Java 21 REST API for shortening URLs. No authentication — every
endpoint is anonymous and public. This doc explains what the backend does; see
[`schemas.md`](./schemas.md) for data shapes and [`../openapi.yml`](../openapi.yml)
for the formal API contract.

## Features

| Feature | Description |
|---|---|
| Shorten a URL | Submit a long URL, get back a short code. Identical URLs (after normalization) return the same code — no duplicate rows. |
| Redirect | Visiting `/{shortCode}` issues a 302 redirect to the original URL and increments a click counter. |
| Expiry | A short URL can optionally expire at a given timestamp. After that, redirects return `410 Gone` instead of redirecting. |
| Click count | Every successful redirect increments a counter, visible via the stats endpoint. |
| Stats lookup | `/api/urls/{shortCode}` returns metadata (original URL, timestamps, click count) without triggering a redirect or click increment. |

## How shortening works

1. **Normalize** — the submitted URL is canonicalized: scheme/host lowercased, default
   ports (`:80` for http, `:443` for https) stripped, trailing slash on non-root paths
   removed, fragment (`#...`) dropped. `example.com/path` and `HTTPS://Example.com:443/path/`
   both normalize the same way, but query strings are preserved as-is (not sorted).
2. **Dedup check** — if a row already exists for that exact normalized URL, its existing
   short code is returned immediately (no new row, no new code).
3. **Code generation** — otherwise, `SHA-256(normalized URL)` is taken mod `62^8` and
   Base62-encoded into a fixed 8-character code (`[0-9a-zA-Z]{8}`).
4. **Collision handling** — if that code is already taken by a *different* URL (a genuine
   hash collision, not a dedup hit), the generator retries with a salt appended to the
   input, up to 5 extra attempts. Exhausting all attempts returns `500`.

## Endpoints

| Method | Path | Purpose | Success | Failure |
|---|---|---|---|---|
| `POST` | `/api/urls` | Create/dedupe a short URL | `201 Created` | `400` invalid URL/validation |
| `GET` | `/{shortCode}` | Redirect + increment clicks | `302 Found` (`Location` header) | `404` unknown code, `410` expired |
| `GET` | `/api/urls/{shortCode}` | Read stats, no side effects | `200 OK` | `404` unknown code |

All error responses share one shape: `{ "error": "<message>" }`.

## What's NOT implemented yet (Phase 3 / not built)

- **Authentication** — there is no login, API key, or per-user ownership of short URLs.
  Anyone can create or view any short URL's stats.
- **CORS** — no CORS configuration exists yet. If your frontend runs on a different
  origin (e.g. `localhost:5173` calling `localhost:8080`), browser requests will be
  blocked until CORS is configured on the backend. Flag this to the backend team before
  wiring up cross-origin calls.
- **Custom aliases** — short codes are always the generated 8-character hash-derived
  code; there's no way to request a specific slug.
- **Rate limiting / abuse protection** — none.
- **Pagination / listing** — there is no endpoint to list all short URLs; you must
  already know a short code to fetch its stats.

## Tech stack (for context, not required to build a frontend)

Java 21, Spring Boot 3.3.5 (Web, Data JPA, Validation), PostgreSQL, Flyway migrations,
Hibernate (`ddl-auto: validate`). See [`../pom.xml`](../pom.xml) for exact versions.

## Base URL

Locally: `http://localhost:8080` (see `src/main/resources/application.yml`,
`server.port: 8080`). No path prefix beyond `/api/urls` and the root-level redirect
route — there is no `/api/v1` versioning yet.
