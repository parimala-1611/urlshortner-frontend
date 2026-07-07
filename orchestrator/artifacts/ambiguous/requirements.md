# Requirements — Ambiguous: "Add Analytics"

## Raw input

"Add analytics to the URL shortener."

## Why this is ambiguous

"Analytics" alone doesn't specify:
- **What** to measure — total clicks over time? click velocity? unique visitors
  (needs a client identifier we don't collect)? geography (needs IP geolocation)?
  device/browser breakdown (needs user-agent parsing)?
- **How it's surfaced** — a new API field, a new endpoint, a dashboard UI, an
  export/report, a webhook?
- **Retention/granularity** — real-time, daily rollups, all-time totals only?
- **Who consumes it** — the link creator only (needs auth, which doesn't exist yet),
  or anyone who knows the short code (consistent with this API's current no-auth
  model)?

There is no human available synchronously inside an automated pipeline stage to
resolve this, so per this project's governance policy, the requirements stage
must make its interpretation and assumptions explicit and **pause for human
approval before design/implementation proceed** — getting this wrong would mean
building the wrong feature entirely, which is exactly the kind of high-impact,
hard-to-reverse decision that warrants a checkpoint.

## Assumptions

Given the existing system already has `clickCount` (a simple lifetime total) and
no authentication, user tracking, or existing dashboard, this interpretation stays
consistent with the project's current scope and no-auth model:

1. **"Analytics" = two concrete, low-effort-high-value metrics**: daily click
   counts (a time series showing click volume by day) and top referrers (which
   sites/pages are driving clicks, from the HTTP `Referer` header). Both are
   derivable from data we can start collecting immediately, with no new user
   input required.
2. **No unique-visitor tracking** — would require a client identifier (cookie,
   fingerprint, IP hashing) which has its own privacy/compliance implications
   out of scope for this pass. Explicitly deferred.
3. **No geography or device/browser breakdown** — would require IP geolocation
   or user-agent parsing, both meaningfully larger scope than "add analytics"
   implies for a first pass. Explicitly deferred.
4. **Surfaced via a new dedicated endpoint** (`GET /api/urls/{shortCode}/analytics`),
   not bolted onto the existing stats endpoint — keeps the existing stats
   endpoint's response shape and query cost unchanged for callers who don't need
   analytics, and mirrors the precedent already set by the QR code feature
   (new capability = new endpoint, not a modified existing one).
5. **No new UI/dashboard** — matches "no new UI" scope; this is an API-only
   capability, consistent with the rest of this backend-only project.
6. **Same access model as the rest of the API** — anyone with a valid `shortCode`
   can view its analytics (no auth exists to restrict it further; consistent
   with the existing stats endpoint's behavior).
7. **Data collection starts now, not retroactively** — existing short URLs will
   have empty/zero analytics until new clicks occur after this ships. Backfilling
   historical data isn't possible (raw per-click data was never captured before
   this change, only the aggregate `clickCount`).

## Acceptance criteria

1. `GET /api/urls/{shortCode}/analytics` returns `200` with total clicks, a
   daily click-count breakdown, and a top-referrers breakdown (referrer + count,
   sorted descending, capped at a reasonable limit).
2. Returns `404` for an unknown short code.
3. Every successful redirect (`GET /{shortCode}`) now also records a click event
   (timestamp + referrer) for later aggregation, in the same transaction as the
   existing click-count increment.
4. Requests with no `Referer` header are grouped under a clear `(direct)` label
   rather than being dropped or crashing the aggregation.
