# Building a Frontend Against This API

Everything a frontend needs: base URL, contract, error handling, and gotchas.
Read [`BACKEND.md`](./BACKEND.md) for feature behavior and [`schemas.md`](./schemas.md)
for exact field shapes first — this doc is the practical "how do I wire this up" layer.

## 1. Before you start: enable CORS for your origin

CORS is **disabled by default** (secure by default — no cross-origin browser requests
are allowed until explicitly configured). If your frontend dev server runs on a
different origin than the API (e.g. Vite on `localhost:5173`, CRA on `localhost:3000`,
API on `localhost:8080`), you need the backend to allow your origin first, or requests
will fail with a CORS error even though `curl`/Postman work fine.

Set `app.cors.allowed-origins` in `application.yml` (or via the
`APP_CORS_ALLOWED-ORIGINS` environment variable) to a comma-separated list of origins,
e.g.:

```yaml
app:
  cors:
    allowed-origins: "http://localhost:5173,http://localhost:3000"
```

Alternatively, proxy API calls through your frontend dev server (e.g. Vite's
`server.proxy`, CRA's `"proxy"` field in `package.json`) so the browser only ever talks
to one origin and CORS never comes into play.

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

{ "url": "https://example.com/long/path", "customAlias": "mylink12" }
```
`customAlias` is optional (6-12 alphanumeric chars). `expiresAt` is also optional — if you
don't send one, the backend assigns a default expiry automatically (see point 5 below).

→ `201` with `{ shortCode, shortUrl, originalUrl, createdAt, expiresAt }`. Use
`shortUrl` directly as the display/copy value — don't reconstruct it from `shortCode`
yourself, since the backend already resolves the host. If you requested a `customAlias`,
check the returned `shortCode` to confirm it was actually honored (see point 5).

The `url` field must be a real `http`/`https` URL — the backend rejects non-web schemes,
gibberish text, and filenames (e.g. `report.pdf`) with `400`. Validate this client-side too
for instant feedback (e.g. a Zod schema mirroring: must parse as a URL, scheme is `http`/`https`,
host isn't a known file extension) rather than relying solely on the server round-trip.

### Look up stats (for a "link details" view, click counters, dashboards)
```
GET {baseUrl}/api/urls/{shortCode}
```
→ `200` with `{ shortCode, originalUrl, createdAt, expiresAt, clickCount }`, or `404`.
This does **not** increment the click count and works even on expired links — safe to
poll for a live click-count display. ✅ Implemented as the "link details" section of
`StatsPage`, alongside the QR and analytics endpoints below (`getAnalytics`,
`getQrCodeUrl` in `src/api/client.ts`), fetched independently per `docs/apiflow.md`
Flow 3 so a 404 from one doesn't hide the other two.

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
- **`customAlias` can silently fail to apply.** If the alias you requested is already
  taken, the backend does **not** return an error — it just falls back to a generated
  code. Always read `shortCode` from the response rather than assuming it equals what
  you sent, and consider showing the user "your requested alias wasn't available, here's
  what you got instead" when they differ. ✅ Implemented in `ShortenPage` — see
  `src/lib/validation.ts` for the client-side URL/alias validation and
  `ShortenPage.tsx`'s fallback notice.
- **Links are not permanent by default.** If you don't send `expiresAt`, the backend
  still assigns one (365 days by default) rather than "never expires" — and links are
  hard-deleted some time after they expire (90 days by default). If your product needs
  truly permanent links, you must explicitly send a far-future `expiresAt`.

## 6. Machine-readable contract

The full OpenAPI 3.0 spec (`openapi.yml`) and dependency manifest (`pom.xml`) live in
the backend repo (`UrlShortner`), not this one — pull them from there if you want to
feed the spec to `openapi-typescript`, `orval`, Swagger UI, Postman, or any codegen tool
instead of hand-writing request/response models, or want to see exact backend
dependency versions when filing a backend bug.
