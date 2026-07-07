export interface ShortenRequest {
  url: string;
  expiresAt?: string | null;
  customAlias?: string | null;
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

export interface DailyClickCount {
  date: string;
  count: number;
}

export interface ReferrerCount {
  referrer: string;
  count: number;
}

export interface AnalyticsResponse {
  shortCode: string;
  totalClicks: number;
  dailyClickCounts: DailyClickCount[];
  topReferrers: ReferrerCount[];
}
