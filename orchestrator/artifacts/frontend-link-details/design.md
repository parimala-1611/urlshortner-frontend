# Design — Frontend: Link Details (QR + Analytics)

## Approach

`src/api/client.ts` gains `getAnalytics(shortCode)` (JSON GET via the existing
`request<T>` helper) and `getQrCodeUrl(shortCode)` (returns a plain URL string, not a
`fetch` call — the QR endpoint returns raw PNG bytes, so it's consumed directly as an
`<img src>` and the browser does the fetching). `StatsPage` gains a `viewingCode` state
set whenever a lookup is triggered (route change or form submit), driving three
independent things: the existing stats fetch, a new `lookupAnalytics` fetch, and the
QR `<img>`'s `src` — none gated on either of the others succeeding, so a 404 from one
never hides the other two, per `docs/apiflow.md` Flow 3's explicit warning against
`Promise.all`.

The daily-clicks visualization is a new `DailyClicksChart` component: a minimal inline
SVG bar chart (no charting library — this is one small chart in an otherwise
dependency-light app). Consulted the `dataviz` skill before building it: single-series
magnitude-over-time is a bar-per-day chart, colored with the skill's default sequential
blue (`#2a78d6` light / `#3987e5` dark, applied as a CSS custom property so Tailwind's
existing `dark:` convention in this codebase still drives the swap), bars capped
at a fixed width with rounded top corners and square baselines, a single hairline
baseline (no gridlines needed for one series), the peak day direct-labeled (per the
skill's "label selectively" rule) rather than every bar, a native SVG `<title>` per bar
as the hover layer, and a visually-hidden `<table>` as the accessible data-table
fallback.

## Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| Fetch independence | Three separate `useEffect`/handler-triggered async calls, none awaited against each other | Directly matches `docs/apiflow.md` Flow 3's explicit guidance: firing in parallel via `Promise.all` fails fast on the first rejection and loses the other two results. |
| QR consumption | Plain URL string (`getQrCodeUrl`), not a `fetch`-wrapped client function | The endpoint returns `image/png` bytes, not JSON — forcing it through the shared JSON `request<T>` helper would mean an unnecessary blob round-trip when the browser can just load the `<img>` directly. |
| QR failure handling | `onError` on the `<img>` flips a `qrFailed` flag, replacing the image with a text fallback | jsdom/browsers don't reject a failed image load as a JS exception — `onError` is the only signal, and it needs to be handled explicitly or a broken-image icon would render instead. |
| Chart implementation | Hand-rolled inline SVG, not a charting library | One chart, small data volumes (daily counts, capped by link lifetime), and this app currently has zero runtime chart dependencies — adding one for a single bar chart isn't proportionate. |
| Zero-filling gaps | Done inside `DailyClicksChart`, not by the caller | `dailyClickCounts` omitting zero-click days is an API-level detail (`docs/apiflow.md`); keeping the fill logic inside the chart component means any other future consumer of the raw analytics response doesn't need to remember to do it too. |

## Impacted files

- `src/api/types.ts` — `AnalyticsResponse`, `DailyClickCount`, `ReferrerCount`.
- `src/api/client.ts` — `getAnalytics`, `getQrCodeUrl`.
- `src/pages/StatsPage.tsx` — QR section, analytics section, independent fetches.
- `src/components/DailyClicksChart.tsx` — new.
- `src/pages/StatsPage.test.tsx`, `src/components/DailyClicksChart.test.tsx` — new.
- `docs/FRONTEND_INTEGRATION.md` — mark Flow 3 as implemented.

## Risks / trade-offs

- **No caching of the QR image across re-renders/navigations** beyond normal browser
  HTTP caching (which the backend doesn't opt into via headers) — acceptable per
  `docs/apiflow.md`'s own note that this is a client concern to revisit only if it
  becomes a real problem, not a correctness issue today.
- **Hand-rolled SVG chart instead of a library** trades some feature headroom (no
  zoom/pan, no automatic responsive re-layout beyond `viewBox` scaling) for zero new
  runtime dependencies — revisit if the analytics view grows more chart types.
