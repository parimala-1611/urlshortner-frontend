# Building a Frontend Against This API

Everything a frontend needs: base URL, contract, error handling, and gotchas.
Read [`BACKEND.md`](./BACKEND.md) for feature behavior and [`schemas.md`](./schemas.md)
for exact field shapes first — this doc is the practical "how do I wire this up" layer.

## 1. Before you start: CORS is not configured

The backend has **no CORS configuration**. If your frontend dev server runs on a
different origin than the API (e.g. Vite on `localhost:5173`, CRA on `localhost:3000`,
API on `localhost:8080`), browser requests will fail with a CORS error even though
`curl`/Postman work fine.

Options, in order of least effort:
- Ask the backend owner to add a `WebMvcConfigurer` CORS mapping (or `@CrossOrigin`) for
  your dev origin before you start integration.
- Proxy API calls through your frontend dev server (e.g. Vite's `server.proxy`, CRA's
  `"proxy"` field in `package.json`) so the browser only ever talks to one origin.

## 2. Base URL

```
http://localhost:8080
```

No versioning prefix, no `/api/v1` — just `/api/urls` and the root-level `/{shortCode}`
redirect route. Put this behind an env var (`VITE_API_BASE_URL`, `NEXT_PUBLIC_API_URL`,
etc.) from day one so it's swappable for staging/prod later.

## 3. The three calls you'll make

### Create a short URL
```
POST {baseUrl}/api/urls
Content-Type: application/json

{ "url": "https://example.com/long/path" }
```
→ `201` with `{ shortCode, shortUrl, originalUrl, createdAt, expiresAt }`. Use
`shortUrl` directly as the display/copy value — don't reconstruct it from `shortCode`
yourself, since the backend already resolves the host.

### Look up stats (for a "link details" view, click counters, dashboards)
```
GET {baseUrl}/api/urls/{shortCode}
```
→ `200` with `{ shortCode, originalUrl, createdAt, expiresAt, clickCount }`, or `404`.
This does **not** increment the click count and works even on expired links — safe to
poll for a live click-count display.

### Follow / test a short link
```
GET {baseUrl}/{shortCode}
```
This is the actual redirect endpoint end users hit — don't call it from your app just
to "check if a link works," since it increments the click counter and returns a
redirect response, not JSON. For validity checks, use the stats endpoint instead and
compare `expiresAt` against the current time client-side, or just attempt the redirect
in an actual `<a href>`/browser navigation.

## 4. Error handling pattern

Every non-2xx response is `{ "error": "<human-readable message>" }`. Branch on the
**HTTP status code**, not the message text (message strings aren't a stable contract):

| Status | Meaning | Suggested UI |
|---|---|---|
| `400` | Bad input (blank/invalid URL) | Inline form validation error |
| `404` | Short code doesn't exist | "Link not found" page |
| `410` | Short code existed but expired | "This link has expired" page (distinct from 404) |
| `500` | Rare — code generation exhausted retries | Generic "something went wrong," suggest retry |

## 5. Things that will surprise you if you don't know them upfront

- **Submitting the same URL twice returns the same `shortCode`.** This is intentional
  dedup, not a bug — don't assume every `POST` creates a new row.
  This includes the `expiresAt` on the response: if a URL was
  already shortened *without* an expiry, sending it again *with* an expiry
  will **not** update the expiry — you'll just get back the original response.
- **`originalUrl` in the response may not match what you typed.** It's normalized
  (lowercased host, no trailing slash, etc.) — don't do a strict string-equality check
  against your input field.
- **No listing endpoint.** There's no `GET /api/urls` to list all shortened links —
  you must persist/track `shortCode` values client-side (or add such an endpoint on
  the backend) if you want a history/dashboard view.
- **No auth, no ownership.** Anyone with a `shortCode` can view its stats. Don't build
  a "my links" feature assuming per-user isolation exists — it doesn't yet.

## 6. Machine-readable contract

[`../openapi.yml`](../openapi.yml) has the full OpenAPI 3.0 spec — feed it to
`openapi-typescript`, `orval`, Swagger UI, Postman, or any codegen tool to generate
typed request/response models instead of hand-writing them.

## 7. Backend dependencies (for context only — not things you install)

See [`../pom.xml`](../pom.xml) for exact versions. Listed here so a frontend dev knows
what they're integrating with, e.g. when reading error messages or filing backend bugs:

| Dependency | Role |
|---|---|
| Spring Boot Web | REST controllers, JSON serialization |
| Spring Boot Data JPA + Hibernate | ORM (`ddl-auto: validate`, schema owned by Flyway) |
| Spring Boot Validation | `@Valid` request body validation (blank-URL check) |
| Flyway | Database schema migrations |
| PostgreSQL driver | Database connectivity |
| Testcontainers (test-only) | Integration tests against a real Postgres |
