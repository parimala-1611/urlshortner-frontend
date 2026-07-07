# Requirements — Greenfield: QR Code Generation

## Raw input

"Add QR code generation for short URLs."

## Interpretation

A well-defined, non-ambiguous request: given an existing short code, provide a
scannable QR code image that encodes the short link, so users can share links
via print/screen without typing them.

## Normalized engineering problem

Add a new read-only endpoint that, given a valid `shortCode`, returns a PNG
image encoding the full short URL (e.g. `http://localhost:8080/{shortCode}`).
It must:
- Return `404` for an unknown short code (reuse existing lookup semantics).
- Not require the code to be non-expired — a QR code is just an encoding of
  the link, not a redirect; whether the link still works when scanned is a
  separate concern already handled by the existing redirect endpoint.
- Not increment the click counter (mirrors the existing stats endpoint's
  side-effect-free semantics, not the redirect endpoint's).

## Out of scope

- Custom QR styling/branding/logo embedding.
- Configurable QR size/error-correction level via query params (fixed
  defaults are enough for a first version).
- Caching/pre-generation of QR images (generated on demand; acceptable given
  QR encoding is fast and this is a low-traffic prototype).

## Acceptance criteria

1. `GET /api/urls/{shortCode}/qr` returns `200` with `Content-Type: image/png`
   and a valid QR-encoded PNG for an existing short code.
2. Returns `404` with the standard `ErrorResponse` shape for an unknown code.
3. Works for both expired and non-expired codes (no expiry check).
4. Decoding the returned PNG yields exactly the `shortUrl` value that
   `POST /api/urls` would have produced for that code.
