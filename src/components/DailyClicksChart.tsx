import type { DailyClickCount } from '../api/types';

const BAR_WIDTH = 10;
const BAR_GAP = 2;
const BAR_RADIUS = 3;
const CHART_HEIGHT = 120;
const AXIS_HEIGHT = 24;

// The backend only returns days that had at least one click (see docs/apiflow.md
// Flow 3) - chart consumers need the gaps filled in as zero, or a sparse click
// history reads as a shorter one than it really is.
function zeroFill(data: DailyClickCount[]): DailyClickCount[] {
  if (data.length === 0) return [];
  const byDate = new Map(data.map((d) => [d.date, d.count]));
  const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date));
  const start = new Date(sorted[0].date);
  const end = new Date(sorted[sorted.length - 1].date);

  const filled: DailyClickCount[] = [];
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const iso = d.toISOString().slice(0, 10);
    filled.push({ date: iso, count: byDate.get(iso) ?? 0 });
  }
  return filled;
}

function roundedTopBarPath(x: number, yTop: number, width: number, height: number): string {
  const r = Math.min(BAR_RADIUS, height, width / 2);
  const yBase = yTop + height;
  if (r <= 0) {
    return `M ${x},${yBase} L ${x},${yTop} L ${x + width},${yTop} L ${x + width},${yBase} Z`;
  }
  return [
    `M ${x},${yBase}`,
    `L ${x},${yTop + r}`,
    `Q ${x},${yTop} ${x + r},${yTop}`,
    `L ${x + width - r},${yTop}`,
    `Q ${x + width},${yTop} ${x + width},${yTop + r}`,
    `L ${x + width},${yBase}`,
    'Z',
  ].join(' ');
}

export function DailyClicksChart({ data }: { data: DailyClickCount[] }) {
  const filled = zeroFill(data);

  if (filled.length === 0) {
    return <p className="text-sm text-slate-400">No clicks yet.</p>;
  }

  const max = Math.max(...filled.map((d) => d.count), 1);
  const width = filled.length * (BAR_WIDTH + BAR_GAP);
  const baselineY = CHART_HEIGHT;
  const peakIndex = filled.reduce((best, d, i) => (d.count > filled[best].count ? i : best), 0);

  return (
    <div className="[--bar-fill:#2a78d6] dark:[--bar-fill:#3987e5]">
      <svg
        role="img"
        aria-label={`Daily clicks from ${filled[0].date} to ${filled[filled.length - 1].date}, peak ${max} clicks`}
        viewBox={`0 0 ${width} ${CHART_HEIGHT + AXIS_HEIGHT}`}
        className="h-32 w-full"
        preserveAspectRatio="none"
      >
        <line
          x1={0}
          y1={baselineY}
          x2={width}
          y2={baselineY}
          className="stroke-slate-300 dark:stroke-slate-700"
          strokeWidth={1}
        />
        {filled.map((d, i) => {
          const barHeight = (d.count / max) * (CHART_HEIGHT - 8);
          const x = i * (BAR_WIDTH + BAR_GAP);
          return (
            <path key={d.date} d={roundedTopBarPath(x, baselineY - barHeight, BAR_WIDTH, barHeight)} fill="var(--bar-fill)">
              <title>{`${d.date}: ${d.count} click${d.count === 1 ? '' : 's'}`}</title>
            </path>
          );
        })}
        <text
          x={peakIndex * (BAR_WIDTH + BAR_GAP) + BAR_WIDTH / 2}
          y={baselineY - (filled[peakIndex].count / max) * (CHART_HEIGHT - 8) - 4}
          textAnchor="middle"
          className="fill-slate-500 text-[8px] dark:fill-slate-400"
        >
          {max}
        </text>
        <text x={0} y={CHART_HEIGHT + 16} className="fill-slate-400 text-[8px]">
          {filled[0].date}
        </text>
        <text x={width} y={CHART_HEIGHT + 16} textAnchor="end" className="fill-slate-400 text-[8px]">
          {filled[filled.length - 1].date}
        </text>
      </svg>
      <table className="sr-only">
        <caption>Daily clicks</caption>
        <thead>
          <tr>
            <th>Date</th>
            <th>Clicks</th>
          </tr>
        </thead>
        <tbody>
          {filled.map((d) => (
            <tr key={d.date}>
              <td>{d.date}</td>
              <td>{d.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
