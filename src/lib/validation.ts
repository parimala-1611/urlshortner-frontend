// Client-side mirrors of the backend's validation rules (see docs/apiflow.md Flow 1
// and docs/FRONTEND_INTEGRATION.md #3) so users get instant feedback instead of a
// round-trip 400.

const FILE_EXTENSION_PATTERN =
  /\.(pdf|docx?|xlsx?|pptx?|zip|rar|7z|exe|dmg|png|jpe?g|gif|svg|txt|csv|mp3|mp4|mov|avi)$/i;

export function validateUrl(input: string): string | null {
  const trimmed = input.trim();
  if (!trimmed) {
    return 'Enter a URL.';
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return 'Enter a valid URL, including http:// or https://.';
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return 'URL must use http or https.';
  }

  if (FILE_EXTENSION_PATTERN.test(parsed.hostname)) {
    return 'That looks like a filename, not a website address.';
  }

  return null;
}

const CUSTOM_ALIAS_PATTERN = /^[a-zA-Z0-9]{6,12}$/;

export function validateCustomAlias(input: string): string | null {
  const trimmed = input.trim();
  if (!trimmed) {
    return null; // optional
  }

  if (!CUSTOM_ALIAS_PATTERN.test(trimmed)) {
    return 'Custom alias must be 6-12 letters or numbers.';
  }

  return null;
}
