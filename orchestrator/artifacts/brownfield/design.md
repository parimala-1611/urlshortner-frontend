# Design — Brownfield: CORS Configuration

## Approach

New `CorsConfig` (`com.urlshortener.config`, a new package) implements Spring's
`WebMvcConfigurer.addCorsMappings`. Allowed origins come from a single
comma-separated `application.yml` property, parsed once in the constructor.

## Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| Default policy | **Secure by default**: empty property = no origins allowed, CORS mapping not registered at all | Avoids silently opening up the API the moment this ships; an operator must explicitly opt in per environment. Matches this repo's existing pattern of conservative defaults (e.g. strict URL validation, default expiry). |
| Configuration shape | Single property `app.cors.allowed-origins` (comma-separated string) | Simplest possible config surface; avoids introducing a list-of-objects YAML structure for what's fundamentally a flat list. |
| Scope of mapping | `/**` (all paths), methods `GET`/`POST` | CORS is cross-cutting for this API; scoping per-endpoint would need updating every time a new endpoint is added and gives no real security benefit here (there's no auth to bypass). |
| Where it lives | New `config` package, not inside `web` | This is infrastructure/cross-cutting configuration, not a request-handling class — keeping it out of `web` (which currently holds controllers/DTOs/exception handling) matches the existing package-by-responsibility layout. |

## Impacted files

- `src/main/java/com/urlshortener/config/CorsConfig.java` — new.
- `src/main/resources/application.yml` — new `app.cors.allowed-origins` property (empty default).
- `src/test/java/com/urlshortener/config/CorsConfigTest.java` — new.
- `docs/BACKEND.md` — replace the "no CORS" limitation with how it now works.
- `docs/FRONTEND_INTEGRATION.md` — replace the "no CORS" warning with configuration
  instructions for local frontend dev.

## Risks / trade-offs

- **Wildcard-path mapping (`/**`)**: broad, but there's no auth/session state in this
  API for CORS to inadvertently expose (no cookies, no per-user data) — the risk
  profile is low. Revisit if authentication is added later (Phase 3+), since CORS
  + credentials is a much more sensitive combination.
- **No per-environment YAML profiles yet**: a single flat property is fine for now
  given this repo doesn't yet have separate `application-{profile}.yml` files; would
  need revisiting if/when environment-specific config is introduced.
