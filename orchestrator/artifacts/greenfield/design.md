# Design — Greenfield: QR Code Generation

## Approach

New `QrCodeService` (`com.urlshortener.service`) wraps ZXing's `QRCodeWriter`
+ `MatrixToImageWriter` to encode a URL string into PNG bytes. New controller
method on the existing `ShortUrlController` (`GET /{shortCode}/qr` under the
`/api/urls` prefix) reuses `ShortUrlService.getStats(shortCode)` for lookup
(same side-effect-free semantics as the existing stats endpoint), then hands
the resolved `shortUrl` to `QrCodeService`.

## Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| QR library | ZXing (`com.google.zxing:core` + `:javase`) | Industry-standard, MIT-licensed, actively maintained. Hand-rolling Reed-Solomon error correction and QR matrix placement is high-effort and high-risk for a "production-quality" deliverable. Confirmed with user before adding. |
| Lookup path | Reuse `ShortUrlService.getStats` | Already side-effect-free (no click increment) and already throws `ShortUrlNotFoundException` → existing `GlobalExceptionHandler` mapping to `404` needs no changes. |
| Expiry check | None | Per requirements: a QR code just encodes the link; expiry is enforced at redirect time, not at encoding time. |
| Image size | Fixed 300x300px, PNG, default ZXing error-correction (L) | No requirement for configurability in v1; keeps the endpoint simple (no query params to validate). |
| Response type | Raw `image/png` bytes via `ResponseEntity<byte[]>` | Matches how a browser/`<img src>` tag would consume this directly; no JSON wrapper needed. |

## Impacted files

- `pom.xml` — add ZXing dependencies.
- `src/main/java/com/urlshortener/service/QrCodeService.java` — new.
- `src/main/java/com/urlshortener/web/ShortUrlController.java` — new endpoint method.
- `src/test/java/com/urlshortener/service/QrCodeServiceTest.java` — new.
- `src/test/java/com/urlshortener/web/ShortUrlControllerTest.java` — new test cases.
- `docs/BACKEND.md`, `docs/schemas.md`, `openapi.yml` — document the new endpoint.

## Risks / trade-offs

- **New third-party dependency**: ZXing pulls in `core` + `javase`; both are
  small, widely used, and have no known critical CVEs at time of writing.
  Mitigation: Dependabot (already configured in this repo) will flag future
  vulnerabilities.
- **No caching**: every request re-encodes the QR image. Acceptable for this
  prototype's traffic; would need revisiting (e.g. HTTP caching headers, or
  a cache keyed by shortCode) if this became a hot path.
