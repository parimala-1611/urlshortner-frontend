import type { ErrorResponse, ShortenRequest, ShortenResponse, ShortUrlStatsResponse } from './types';

// Empty string plays nicely with the Vite dev proxy (see vite.config.ts), which
// forwards /api/* to the backend so the browser never makes a cross-origin request.
// Set VITE_API_BASE_URL for environments where the frontend isn't proxied.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ErrorResponse | null;
    throw new ApiError(res.status, body?.error ?? `Request failed with status ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export function createShortUrl(payload: ShortenRequest): Promise<ShortenResponse> {
  return request<ShortenResponse>('/api/urls', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getShortUrlStats(shortCode: string): Promise<ShortUrlStatsResponse> {
  return request<ShortUrlStatsResponse>(`/api/urls/${encodeURIComponent(shortCode)}`);
}
