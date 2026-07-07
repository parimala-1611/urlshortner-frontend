# Requirements — Frontend: Custom Alias Support

## Raw input

"Implement the new features according to backend APIs and features" — scoped here to
Flow 1 of `docs/apiflow.md` (create a short link), which the backend already supports
(`customAlias`, strict URL validation) but this frontend doesn't yet exercise.

## Interpretation

A well-defined, non-ambiguous request: the backend has supported `customAlias` and
stricter server-side URL validation for a while (`docs/FRONTEND_INTEGRATION.md`
sections 3 and 5 already document both), but `ShortenPage` never sends `customAlias`
and relies entirely on the server round-trip for validation. Close that gap.

## Normalized engineering problem

1. Let a user optionally request a custom alias when creating a short link.
2. Validate the URL and the alias client-side before hitting the network, mirroring the
   backend's rules, so invalid input is caught instantly instead of via a `400`
   round-trip.
3. Handle the backend's documented silent-fallback behavior: if the requested alias was
   already taken, the backend returns `200`/`201` with a *different* `shortCode`
   instead of an error. The UI must detect this and tell the user, rather than silently
   showing them a link they didn't ask for.

## Out of scope

- Alias *availability* pre-check (a separate `GET` before submit) — the backend has no
  such endpoint; the only way to know is to submit and compare.
- Editing/reserving an alias after a link already exists (no such backend endpoint).
- Server-side validation changes — this is a client-only, backend-API-compatible
  addition (`customAlias` was already an accepted, optional request field).

## Acceptance criteria

1. `ShortenPage` has an optional "Custom alias" field (6-12 alphanumeric characters,
   per the backend's documented rule).
2. Submitting an invalid URL (bad scheme, unparseable, filename-shaped host) shows an
   inline error and makes **no** network call.
3. Submitting a malformed alias (wrong length/characters) shows an inline error and
   makes **no** network call.
4. Submitting a valid URL with a valid (or blank) alias sends `customAlias` in the
   `POST /api/urls` payload.
5. If the response's `shortCode` differs from the requested alias, the result panel
   shows a distinct, non-error notice explaining the fallback. If it matches (or no
   alias was requested), no such notice appears.
