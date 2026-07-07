import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DailyClicksChart } from './DailyClicksChart';

describe('DailyClicksChart', () => {
  it('shows a placeholder when there is no data', () => {
    render(<DailyClicksChart data={[]} />);
    expect(screen.getByText(/no clicks yet/i)).toBeInTheDocument();
  });

  it('zero-fills gaps between the first and last date', () => {
    const { container } = render(
      <DailyClicksChart
        data={[
          { date: '2026-07-06', count: 2 },
          { date: '2026-07-08', count: 3 },
        ]}
      />,
    );

    const rows = container.querySelectorAll('table tbody tr');
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent('2026-07-06');
    expect(rows[0]).toHaveTextContent('2');
    expect(rows[1]).toHaveTextContent('2026-07-07');
    expect(rows[1]).toHaveTextContent('0');
    expect(rows[2]).toHaveTextContent('2026-07-08');
    expect(rows[2]).toHaveTextContent('3');
  });

  it('renders one bar per day with a per-bar tooltip', () => {
    const { container } = render(
      <DailyClicksChart
        data={[
          { date: '2026-07-06', count: 2 },
          { date: '2026-07-07', count: 0 },
          { date: '2026-07-08', count: 3 },
        ]}
      />,
    );

    const titles = Array.from(container.querySelectorAll('path > title')).map((t) => t.textContent);
    expect(titles).toEqual([
      '2026-07-06: 2 clicks',
      '2026-07-07: 0 clicks',
      '2026-07-08: 3 clicks',
    ]);
  });
});
