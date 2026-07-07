# Requirements — Frontend: Link Details (QR + Analytics)

## Raw input

"Implement the new features according to backend APIs and features" — scoped here to
Flow 3 of `docs/apiflow.md` (link details view: stats + QR + analytics), which the
backend already exposes but this frontend doesn't call at all for QR/analytics.

## Interpretation

A well-defined, non-ambiguous request: `docs/apiflow.md` explicitly describes a
"link details" page pattern — fetch stats, QR, and analytics for a `shortCode` in
parallel, each handled independently since each can 404 on its own. `StatsPage`
already implements the stats half; QR and analytics are entirely missing.

## Normalized engineering problem

1. Given a `shortCode` (from the route or the lookup form, same as today), fetch QR
   and analytics data alongside the existing stats fetch — independently, not gated on
   each other's success, per the documented flow.
2. Render the QR code as an image.
3. Render analytics: total clicks, a daily-clicks visualization, and a top-referrers
   list.
4. Each of the three sections must degrade independently: an analytics 404 must not
   hide stats that loaded fine, and vice versa.

## Out of scope

- Caching/pre-fetching the QR blob (the backend sends no caching headers; per
  `docs/apiflow.md` this is a client concern to revisit only if it becomes a problem).
- Any chart interaction beyond a per-day hover tooltip (no date-range picker, no
  zoom) — the analytics endpoint has no query parameters to filter by, so there's
  nothing to control.
- A dedicated referrer visualization beyond the ranked list the endpoint already
  returns (`topReferrers`, capped at 10, pre-sorted).

## Acceptance criteria

1. Visiting `/stats/:shortCode` for a code that exists shows a QR `<img>` pointing at
   `GET /api/urls/{shortCode}/qr`.
2. If the QR request fails to load, the QR section shows a fallback message instead of
   a broken image, and does not affect the stats or analytics sections.
3. The analytics section shows total clicks, a chart of daily click counts with gaps
   (days with zero clicks, which the endpoint omits) visually zero-filled, and the
   top-referrers list.
4. If analytics 404s (e.g., a code with no click history) while stats succeeds, stats
   still renders normally and analytics shows its own "not available" message.
