import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ShortenPage } from './ShortenPage';

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>();
  return { ...actual, createShortUrl: vi.fn() };
});

import { createShortUrl } from '../api/client';

const mockedCreateShortUrl = vi.mocked(createShortUrl);

function renderPage() {
  return render(
    <MemoryRouter>
      <ShortenPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  mockedCreateShortUrl.mockReset();
});

describe('ShortenPage', () => {
  it('renders the custom alias field', () => {
    renderPage();
    expect(screen.getByLabelText(/custom alias/i)).toBeInTheDocument();
  });

  it('blocks submit and shows an error for an invalid URL without calling the API', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByLabelText(/long url/i), 'not a url');
    await user.click(screen.getByRole('button', { name: /shorten/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/valid URL/i);
    expect(mockedCreateShortUrl).not.toHaveBeenCalled();
  });

  it('blocks submit and shows an error for a malformed custom alias without calling the API', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByLabelText(/long url/i), 'https://example.com');
    await user.type(screen.getByLabelText(/custom alias/i), 'a-b');
    await user.click(screen.getByRole('button', { name: /shorten/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/6-12/);
    expect(mockedCreateShortUrl).not.toHaveBeenCalled();
  });

  it('shows no fallback note when the returned shortCode matches the requested alias', async () => {
    mockedCreateShortUrl.mockResolvedValue({
      shortCode: 'mylink12',
      shortUrl: 'http://localhost:8080/mylink12',
      originalUrl: 'https://example.com',
      createdAt: '2026-07-08T00:00:00Z',
      expiresAt: null,
    });

    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByLabelText(/long url/i), 'https://example.com');
    await user.type(screen.getByLabelText(/custom alias/i), 'mylink12');
    await user.click(screen.getByRole('button', { name: /shorten/i }));

    await waitFor(() => expect(mockedCreateShortUrl).toHaveBeenCalledWith({
      url: 'https://example.com',
      expiresAt: null,
      customAlias: 'mylink12',
    }));
    expect(screen.queryByText(/wasn't available/i)).not.toBeInTheDocument();
  });

  it('shows a fallback note when the returned shortCode differs from the requested alias', async () => {
    mockedCreateShortUrl.mockResolvedValue({
      shortCode: 'generatedX',
      shortUrl: 'http://localhost:8080/generatedX',
      originalUrl: 'https://example.com',
      createdAt: '2026-07-08T00:00:00Z',
      expiresAt: null,
    });

    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByLabelText(/long url/i), 'https://example.com');
    await user.type(screen.getByLabelText(/custom alias/i), 'mylink12');
    await user.click(screen.getByRole('button', { name: /shorten/i }));

    expect(await screen.findByText(/wasn't available/i)).toHaveTextContent('mylink12');
  });
});
