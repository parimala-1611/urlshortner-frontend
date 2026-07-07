# Design — Frontend: Custom Alias Support

## Approach

New `src/lib/validation.ts` holds two pure functions, `validateUrl` and
`validateCustomAlias`, each returning `string | null` (error message or valid) so
`ShortenPage.tsx` can run them synchronously on submit before calling `createShortUrl`.
`ShortenPage` gains a `customAlias` input and a `requestedAlias` piece of state captured
at submit time (not derived from the input after the fact, since the user could edit the
field again while a request is in flight); after a successful response, comparing
`requestedAlias` to `response.shortCode` decides whether to render the fallback notice.

## Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| Validation location | Pure functions in `src/lib/validation.ts`, called from the existing `handleSubmit` | Keeps `ShortenPage` a thin consumer and makes the rules independently unit-testable without rendering the component. |
| URL rule | Must parse via `new URL()`, scheme `http`/`https`, hostname doesn't end in a common file extension | Mirrors the exact rule `docs/FRONTEND_INTEGRATION.md` #3 documents for the backend ("must be a real http/https URL... rejects filenames"). |
| Alias rule | Optional; if present, 6-12 alphanumeric characters | Matches the backend's documented constraint (`docs/apiflow.md` Flow 1: "customAlias is optional (6-12 alphanumeric chars)"). |
| Fallback detection | Compare `response.shortCode` to the alias captured *at submit time*, not the live input state | The input can change (or be cleared) while the request is in flight; comparing against a snapshot avoids a stale/incorrect comparison. |
| Fallback UX | A distinct amber informational panel, separate from the red error banner | The request still succeeded — this isn't an error, it's a "here's what actually happened" notice, so it shouldn't look like one. |

## Impacted files

- `src/api/types.ts` — add `customAlias?: string | null` to `ShortenRequest`.
- `src/lib/validation.ts` — new.
- `src/pages/ShortenPage.tsx` — alias input, client-side validation gate, fallback
  notice.
- `src/lib/validation.test.ts`, `src/pages/ShortenPage.test.tsx` — new.
- `docs/FRONTEND_INTEGRATION.md`, `README.md` — document what's implemented.

## Risks / trade-offs

- **Client-side validation can drift from the backend's actual rules** if the backend
  changes them without a corresponding doc/frontend update — acceptable here since both
  are sourced from the same documented contract (`docs/apiflow.md`), and a mismatch
  fails safely (worst case: an extra round-trip `400`, not a silent bad state).
- **No debounced/live validation** (only on submit) — deliberate, to keep the change
  small and match the existing form's pattern (the URL field has no live validation
  either); can be revisited if product wants inline-as-you-type feedback later.
