import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, createShortUrl } from '../api/client';
import type { ShortenResponse } from '../api/types';
import { CopyButton } from '../components/CopyButton';
import { useHistory } from '../hooks/useHistory';

export function ShortenPage() {
  const [url, setUrl] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [result, setResult] = useState<ShortenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { entries, addEntry, removeEntry } = useHistory();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await createShortUrl({
        url: url.trim(),
        expiresAt: expiresAt ? new Date(expiresAt).toISOString() : null,
      });
      setResult(response);
      addEntry({
        shortCode: response.shortCode,
        shortUrl: response.shortUrl,
        originalUrl: response.originalUrl,
        createdAt: response.createdAt,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Something went wrong. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Shorten a URL</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Submitting the same URL twice returns the same short code — that's dedup, not a bug.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="url" className="mb-1 block text-sm font-medium">
              Long URL
            </label>
            <input
              id="url"
              type="text"
              required
              placeholder="https://example.com/some/long/path"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900"
            />
          </div>

          <div>
            <label htmlFor="expiresAt" className="mb-1 block text-sm font-medium">
              Expires at <span className="font-normal text-slate-400">(optional)</span>
            </label>
            <input
              id="expiresAt"
              type="datetime-local"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900"
            />
          </div>

          {error && (
            <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            {submitting ? 'Shortening…' : 'Shorten'}
          </button>
        </form>

        {result && (
          <div className="mt-6 rounded-md border border-slate-200 p-4 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <a
                href={result.shortUrl}
                target="_blank"
                rel="noreferrer"
                className="truncate font-mono text-sm text-blue-600 hover:underline dark:text-blue-400"
              >
                {result.shortUrl}
              </a>
              <CopyButton text={result.shortUrl} />
            </div>
            <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm text-slate-500 dark:text-slate-400">
              <dt>Original</dt>
              <dd className="truncate">{result.originalUrl}</dd>
              <dt>Created</dt>
              <dd>{new Date(result.createdAt).toLocaleString()}</dd>
              <dt>Expires</dt>
              <dd>{result.expiresAt ? new Date(result.expiresAt).toLocaleString() : 'Never'}</dd>
            </dl>
          </div>
        )}
      </section>

      {entries.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold tracking-tight">Recent links</h2>
          <p className="mt-1 text-xs text-slate-400">
            Tracked in this browser only — the backend has no listing endpoint.
          </p>
          <ul className="mt-3 divide-y divide-slate-200 dark:divide-slate-800">
            {entries.map((entry) => (
              <li key={entry.shortCode} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <Link
                    to={`/stats/${entry.shortCode}`}
                    className="block truncate font-mono text-sm text-blue-600 hover:underline dark:text-blue-400"
                  >
                    {entry.shortUrl}
                  </Link>
                  <p className="truncate text-xs text-slate-400">{entry.originalUrl}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeEntry(entry.shortCode)}
                  className="shrink-0 text-xs text-slate-400 hover:text-red-500"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
