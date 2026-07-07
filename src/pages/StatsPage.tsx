import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError, getAnalytics, getQrCodeUrl, getShortUrlStats } from '../api/client';
import type { AnalyticsResponse, ShortUrlStatsResponse } from '../api/types';
import { DailyClicksChart } from '../components/DailyClicksChart';

export function StatsPage() {
  const { shortCode: routeShortCode } = useParams();
  const navigate = useNavigate();
  const [input, setInput] = useState(routeShortCode ?? '');
  const [stats, setStats] = useState<ShortUrlStatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [viewingCode, setViewingCode] = useState<string | null>(null);
  const [qrFailed, setQrFailed] = useState(false);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  const lookupStats = async (shortCode: string) => {
    setLoading(true);
    setError(null);
    setStats(null);
    try {
      const response = await getShortUrlStats(shortCode);
      setStats(response);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError('No short URL found for that code.');
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Something went wrong. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const lookupAnalytics = async (shortCode: string) => {
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    setAnalytics(null);
    try {
      const response = await getAnalytics(shortCode);
      setAnalytics(response);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setAnalyticsError('No analytics available for that code.');
      } else if (err instanceof ApiError) {
        setAnalyticsError(err.message);
      } else {
        setAnalyticsError('Something went wrong loading analytics.');
      }
    } finally {
      setAnalyticsLoading(false);
    }
  };

  // Stats, QR, and analytics are fetched independently (not Promise.all) per
  // docs/apiflow.md Flow 3 - each endpoint 404s on its own, and one failing
  // must not hide the other two.
  const runLookups = (shortCode: string) => {
    if (!shortCode.trim()) return;
    const trimmed = shortCode.trim();
    setViewingCode(trimmed);
    setQrFailed(false);
    void lookupStats(trimmed);
    void lookupAnalytics(trimmed);
  };

  useEffect(() => {
    if (routeShortCode) {
      setInput(routeShortCode);
      runLookups(routeShortCode);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeShortCode]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    navigate(`/stats/${encodeURIComponent(input.trim())}`);
  };

  const isExpired = stats?.expiresAt != null && new Date(stats.expiresAt).getTime() < Date.now();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Look up stats</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Fetches metadata without following the redirect or incrementing the click count.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          required
          placeholder="Short code, e.g. a1B2c3D4"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
        >
          {loading ? 'Looking up…' : 'Look up'}
        </button>
      </form>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      {stats && (
        <div className="rounded-md border border-slate-200 p-4 dark:border-slate-800">
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm">{stats.shortCode}</span>
            {isExpired && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900 dark:text-amber-200">
                Expired
              </span>
            )}
          </div>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm text-slate-500 dark:text-slate-400">
            <dt>Original</dt>
            <dd className="truncate">{stats.originalUrl}</dd>
            <dt>Created</dt>
            <dd>{new Date(stats.createdAt).toLocaleString()}</dd>
            <dt>Expires</dt>
            <dd>{stats.expiresAt ? new Date(stats.expiresAt).toLocaleString() : 'Never'}</dd>
            <dt>Clicks</dt>
            <dd>{stats.clickCount}</dd>
          </dl>
        </div>
      )}

      {viewingCode && (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-md border border-slate-200 p-4 dark:border-slate-800">
            <h2 className="text-sm font-semibold">QR code</h2>
            {qrFailed ? (
              <p className="mt-2 text-sm text-slate-400">QR code unavailable for that code.</p>
            ) : (
              <img
                src={getQrCodeUrl(viewingCode)}
                alt={`QR code for ${viewingCode}`}
                onError={() => setQrFailed(true)}
                className="mt-3 h-32 w-32"
              />
            )}
          </div>

          <div className="rounded-md border border-slate-200 p-4 dark:border-slate-800">
            <h2 className="text-sm font-semibold">Analytics</h2>
            {analyticsLoading && <p className="mt-2 text-sm text-slate-400">Loading…</p>}
            {analyticsError && <p className="mt-2 text-sm text-slate-400">{analyticsError}</p>}
            {analytics && (
              <div className="mt-3 space-y-4">
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {analytics.totalClicks} total click{analytics.totalClicks === 1 ? '' : 's'}
                </p>
                <DailyClicksChart data={analytics.dailyClickCounts} />
                {analytics.topReferrers.length > 0 && (
                  <div>
                    <h3 className="text-xs font-medium text-slate-500 dark:text-slate-400">Top referrers</h3>
                    <ul className="mt-1 space-y-1 text-sm">
                      {analytics.topReferrers.map((r) => (
                        <li key={r.referrer} className="flex items-center justify-between gap-2">
                          <span className="truncate text-slate-700 dark:text-slate-200">{r.referrer}</span>
                          <span className="shrink-0 text-slate-400">{r.count}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
