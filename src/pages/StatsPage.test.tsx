import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StatsPage } from './StatsPage';

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>();
  return {
    ...actual,
    getShortUrlStats: vi.fn(),
    getAnalytics: vi.fn(),
    getQrCodeUrl: vi.fn((shortCode: string) => `http://localhost:8080/api/urls/${shortCode}/qr`),
  };
});

import { ApiError, getAnalytics, getShortUrlStats } from '../api/client';

const mockedGetStats = vi.mocked(getShortUrlStats);
const mockedGetAnalytics = vi.mocked(getAnalytics);

function renderAt(shortCode: string) {
  return render(
    <MemoryRouter initialEntries={[`/stats/${shortCode}`]}>
      <Routes>
        <Route path="/stats/:shortCode" element={<StatsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const baseStats = {
  shortCode: 'abc123',
  originalUrl: 'https://example.com',
  createdAt: '2026-07-01T00:00:00Z',
  expiresAt: null,
  clickCount: 5,
};

const baseAnalytics = {
  shortCode: 'abc123',
  totalClicks: 5,
  dailyClickCounts: [{ date: '2026-07-08', count: 5 }],
  topReferrers: [{ referrer: 'https://twitter.com', count: 3 }],
};

beforeEach(() => {
  mockedGetStats.mockReset();
  mockedGetAnalytics.mockReset();
});

describe('StatsPage', () => {
  it('renders a QR code image pointed at the right shortCode', async () => {
    mockedGetStats.mockResolvedValue(baseStats);
    mockedGetAnalytics.mockResolvedValue(baseAnalytics);

    renderAt('abc123');

    const img = await screen.findByAltText(/qr code for abc123/i);
    expect(img).toHaveAttribute('src', 'http://localhost:8080/api/urls/abc123/qr');
  });

  it('shows a fallback message when the QR image fails to load', async () => {
    mockedGetStats.mockResolvedValue(baseStats);
    mockedGetAnalytics.mockResolvedValue(baseAnalytics);

    renderAt('abc123');

    const img = await screen.findByAltText(/qr code for abc123/i);
    fireEvent.error(img);

    expect(await screen.findByText(/qr code unavailable/i)).toBeInTheDocument();
    expect(screen.queryByAltText(/qr code for abc123/i)).not.toBeInTheDocument();
  });

  it('renders total clicks and top referrers from analytics', async () => {
    mockedGetStats.mockResolvedValue(baseStats);
    mockedGetAnalytics.mockResolvedValue(baseAnalytics);

    renderAt('abc123');

    expect(await screen.findByText(/5 total clicks/i)).toBeInTheDocument();
    expect(await screen.findByText('https://twitter.com')).toBeInTheDocument();
  });

  it('shows stats even when analytics 404s independently', async () => {
    mockedGetStats.mockResolvedValue(baseStats);
    mockedGetAnalytics.mockRejectedValue(new ApiError(404, 'not found'));

    renderAt('abc123');

    expect(await screen.findByText('https://example.com')).toBeInTheDocument();
    expect(await screen.findByText(/no analytics available/i)).toBeInTheDocument();
  });
});
