import { useCallback, useEffect, useState } from 'react';

export interface HistoryEntry {
  shortCode: string;
  shortUrl: string;
  originalUrl: string;
  createdAt: string;
}

const STORAGE_KEY = 'urlshortener.history';

function readHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export function useHistory() {
  const [entries, setEntries] = useState<HistoryEntry[]>(() => readHistory());

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  }, [entries]);

  const addEntry = useCallback((entry: HistoryEntry) => {
    setEntries((prev) => [entry, ...prev.filter((e) => e.shortCode !== entry.shortCode)].slice(0, 50));
  }, []);

  const removeEntry = useCallback((shortCode: string) => {
    setEntries((prev) => prev.filter((e) => e.shortCode !== shortCode));
  }, []);

  const clear = useCallback(() => setEntries([]), []);

  return { entries, addEntry, removeEntry, clear };
}
