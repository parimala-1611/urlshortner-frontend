# Design — Ambiguous: Analytics (Daily Counts + Top Referrers)

## Approach

New `click_events` table logs one row per successful redirect (short URL id,
timestamp, nullable referrer). A new `AnalyticsService` fetches raw events for a
short code and aggregates them **in Java** (not in SQL) into daily counts and
top referrers. A new `GET /api/urls/{shortCode}/analytics` endpoint exposes it.

## Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| Aggregation location | Plain Java (`Collectors.groupingBy` + streams) over raw rows, not SQL `GROUP BY`/`date_trunc` | Keeps the aggregation logic fully unit-testable with plain objects (no DB needed to verify grouping/sorting/limit-N logic is correct) and avoids PostgreSQL-specific SQL inside a repository, trading off transferring more rows per request — acceptable at this project's scale (prototype, not high-traffic). |
| Referrer storage | Nullable `TEXT` column, coalesced to `(direct)` at aggregation time, not storage time | Keeps raw data faithful to what was actually observed (no `Referer` header vs. an empty one are collapsed identically at read time, which is all that matters for reporting). |
| Click recording | Extend `ShortUrlService.resolve()` to accept a referrer and save a `ClickEvent` in the *same* `@Transactional` method that increments `clickCount` | Keeps "a click happened" atomic - one transaction, not two services racing to record two different aspects of the same event. |
| Endpoint shape | New endpoint, not added fields on `ShortUrlStatsResponse` | See requirements.md assumption 4 - keeps the existing stats endpoint's cost/shape unchanged for callers who don't need analytics. |
| Historical backfill | None - out of scope | Raw click data wasn't captured before this change; only backfillable if we consider synthesizing fake history, which would be actively misleading. |

## Impacted files

- `src/main/resources/db/migration/V2__click_events.sql` — new table + index.
- `src/main/java/com/urlshortener/model/ClickEvent.java` — new entity.
- `src/main/java/com/urlshortener/repository/ClickEventRepository.java` — new (single derived query, no native SQL).
- `src/main/java/com/urlshortener/service/AnalyticsService.java` — new (aggregation logic, unit-testable in isolation).
- `src/main/java/com/urlshortener/service/ShortUrlService.java` — `resolve()` extended to accept and record a referrer.
- `src/main/java/com/urlshortener/web/ShortUrlController.java` — new `/analytics` endpoint; `redirect()` now reads the `Referer` header.
- `src/main/java/com/urlshortener/web/dto/{AnalyticsResponse,DailyClickCount,ReferrerCount}.java` — new DTOs.
- Existing `ShortUrlServiceTest`/`ShortUrlControllerTest` — updated for the `resolve()` signature change.
- `docs/BACKEND.md`, `docs/schemas.md`, `openapi.yml` — document the new endpoint and table.

## Risks / trade-offs

- **Unbounded row growth**: `click_events` grows one row per redirect forever
  (no retention policy analogous to `short_urls`' expiry/purge). Acceptable for
  a prototype; flagged as a follow-up (tie click-event retention to the same
  purge job that already exists for expired short URLs, or a separate policy).
- **In-memory aggregation cost**: for a short code with very high click volume,
  fetching all raw events per analytics request could get expensive. Acceptable
  at prototype scale; would need a move to DB-side aggregation or pre-computed
  rollups if this became a hot path — explicitly deferred, not silently ignored.
- **Referrer header is client-supplied and unverified**: it can be spoofed or
  absent (privacy-conscious browsers/extensions increasingly omit it). Analytics
  should be read as directional, not authoritative.
