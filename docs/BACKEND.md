# URL Shortener — Backend Overview

Spring Boot 3.3.5 / Java 21 REST API for shortening URLs. No authentication — every
endpoint is anonymous and public. This doc explains what the backend does; see
[`schemas.md`](./schemas.md) for data shapes and [`../openapi.yml`](../openapi.yml)
for the formal API contract.

## Features

| Feature | Description |
|---|---|
| Shorten a URL | Submit a long URL, get back a short code. Identical URLs (after normalization) return the same code — no duplicate rows. |
| Custom alias | Optionally request your own 6-12 character short code. If it's available it's used as-is; if it's taken, the request silently falls back to the standard hash-based generator instead of erroring. |
| Redirect | Visiting `/{shortCode}` issues a 302 redirect to the original URL and increments a click counter. |
| Expiry | A short URL expires at a given timestamp. If you don't supply one, a default expiry is applied (see Data retention below) — links are not kept forever by default. After expiry, redirects return `410 Gone` instead of redirecting. |
| Click count | Every successful redirect increments a counter, visible via the stats endpoint. |
| Stats lookup | `/api/urls/{shortCode}` returns metadata (original URL, timestamps, click count) without triggering a redirect or click increment. |
| QR code | `/api/urls/{shortCode}/qr` returns a PNG QR code encoding the short link. Works for expired codes too (encoding the link isn't the same as redirecting through it), and doesn't increment the click count. |
| Analytics | `/api/urls/{shortCode}/analytics` returns total clicks, a daily click-count breakdown, and top referrers (from the HTTP `Referer` header on each redirect). See "Analytics" below for exact scope. |
| Strict URL validation | Only real `http`/`https` URLs are accepted — see Validation rules below. |

## How shortening works

1. **Normalize** — the submitted URL is canonicalized: scheme/host lowercased, default
   ports (`:80` for http, `:443` for https) stripped, trailing slash on non-root paths
   removed, fragment (`#...`) dropped. `example.com/path` and `HTTPS://Example.com:443/path/`
   both normalize the same way, but query strings are preserved as-is (not sorted).
2. **Dedup check** — if a row already exists for that exact normalized URL, its existing
   short code is returned immediately (no new row, no new code) — the requested alias and
   expiry are ignored in this case, since the URL was already shortened before.
3. **Custom alias (optional)** — if the request includes `customAlias` and it's not already
   taken, it's used directly as the short code.
4. **Code generation** — otherwise (no alias requested, or the requested alias was taken),
   `SHA-256(normalized URL)` is taken mod `62^8` and Base62-encoded into a fixed 8-character
   code (`[0-9a-zA-Z]{8}`).
5. **Collision handling** — if that code is already taken by a *different* URL (a genuine
   hash collision, not a dedup hit), the generator retries with a salt appended to the
   input, up to 5 extra attempts. Exhausting all attempts returns `500`.

## Validation rules

Only legitimate `http`/`https` URLs are accepted — this is intentional, so the service can't
be used to shorten arbitrary text, local file paths, or non-web URI schemes:

- **Scheme**: must be `http` or `https` (missing scheme defaults to `https`). Other schemes
  (`ftp://`, `mailto:`, `javascript:`, `file://`, etc.) are rejected with `400`.
- **Host shape**: must be a real-looking domain (e.g. `example.com`), a valid IPv4 address,
  or `localhost`. Gibberish text with no domain structure (e.g. `asdkjhasdkjh`) is rejected.
- **File-like hosts blocked**: hosts whose last label matches a common file extension
  (`.exe`, `.pdf`, `.docx`, `.zip`, `.mp3`, etc.) are rejected — this catches people
  accidentally/deliberately submitting a filename instead of a URL (e.g. `malware.exe`).

This is a practical filter, not a full public-suffix/TLD registry check — it won't catch
every conceivable fake domain, but it blocks the concrete cases above.

## Data retention

- **Default expiry**: if a request doesn't include `expiresAt`, the backend assigns one
  automatically (`app.retention.default-expiry-days` in `application.yml`, default **365
  days**). Links are not kept forever unless you explicitly extend that policy.
- **Purge job**: a scheduled job (`app.retention.purge-cron`, default daily at 03:00) hard-deletes
  short URLs that expired more than `app.retention.purge-after-days` ago (default **90 days**
  past `expiresAt`). This is a permanent deletion, not a soft-delete — plan accordingly if you
  need long-term analytics on old links.

## CORS

Cross-origin requests are **disabled by default** (secure by default) and controlled by
a single `application.yml` property: `app.cors.allowed-origins` — a comma-separated list
of origins (e.g. `http://localhost:5173,http://localhost:3000`). Leave it empty (the
default) and no cross-origin browser requests are allowed at all; set it to enable a
specific frontend dev server or production frontend origin. See
[`FRONTEND_INTEGRATION.md`](./FRONTEND_INTEGRATION.md) for exact setup steps.

## Analytics

Scope, deliberately kept narrow (see `orchestrator/artifacts/ambiguous/requirements.md`
for the full ambiguity/assumptions writeup this was built against):

- **Daily click counts** — click volume per calendar day (UTC), derived from a new
  `click_events` row recorded on every successful redirect.
- **Top referrers** — the HTTP `Referer` header seen on each redirect, grouped and
  ranked by count (top 10). Requests with no `Referer` are grouped under `(direct)`.
- **Not included**: unique-visitor tracking, geography, device/browser breakdown, a
  dashboard UI, or historical backfill for clicks that happened before this shipped —
  all explicitly deferred, not overlooked.
- Same access model as the rest of the API: no auth, anyone with a valid `shortCode`
  can view its analytics.

## Endpoints

| Method | Path | Purpose | Success | Failure |
|---|---|---|---|---|
| `POST` | `/api/urls` | Create/dedupe a short URL | `201 Created` | `400` invalid URL/validation |
| `GET` | `/{shortCode}` | Redirect + increment clicks | `302 Found` (`Location` header) | `404` unknown code, `410` expired |
| `GET` | `/api/urls/{shortCode}` | Read stats, no side effects | `200 OK` | `404` unknown code |
| `GET` | `/api/urls/{shortCode}/qr` | PNG QR code for the short link | `200 OK` (`image/png`) | `404` unknown code |
| `GET` | `/api/urls/{shortCode}/analytics` | Daily click counts + top referrers | `200 OK` | `404` unknown code |

All error responses share one shape: `{ "error": "<message>" }`.

## What's NOT implemented yet (Phase 3 / not built)

- **Authentication** — there is no login, API key, or per-user ownership of short URLs.
  Anyone can create or view any short URL's stats.
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
