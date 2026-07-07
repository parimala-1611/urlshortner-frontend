export interface ShortenRequest {
  url: string;
  expiresAt?: string | null;
}

export interface ShortenResponse {
  shortCode: string;
  shortUrl: string;
  originalUrl: string;
  createdAt: string;
  expiresAt: string | null;
}

export interface ShortUrlStatsResponse {
  shortCode: string;
  originalUrl: string;
  createdAt: string;
  expiresAt: string | null;
  clickCount: number;
}

export interface ErrorResponse {
  error: string;
}
