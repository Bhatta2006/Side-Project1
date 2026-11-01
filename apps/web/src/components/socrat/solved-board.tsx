'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface SolvedBoardData {
  show: boolean;
  solved: number;
  total: number;
  by_difficulty: { level: 'easy' | 'medium' | 'hard'; solved: number; total: number }[];
  acceptance: number | null;
  submissions: number;
  active_days: number;
  streak: { current: number; longest: number };
  heatmap: { day: string; count: number }[];
  recent: { id: string; source: 'judge' | 'library'; title: string; level: string; at: number }[];
}

const LEVEL = {
  // Coding-site convention, readable on both themes.
  easy: { label: 'Easy', ink: '#16a06b' },
  medium: { label: 'Medium', ink: '#c88a04' },
  hard: { label: 'Hard', ink: '#dc3b3f' },
} as const;

/** The big ring: solved over everything on offer, split by difficulty like a coding site. */
function Ring({ data }: { data: SolvedBoardData }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  let offset = 0;
  const arcs = data.by_difficulty.map(d => {
    // Each difficulty's slice grows with its share of what is solved; the empty track shows the rest.
    const part = data.total ? (d.solved / data.total) * c : 0;
    const arc = { level: d.level, dash: Math.max(part, d.solved ? 2 : 0), offset };
    offset += part;
    return arc;
  });
  return (
    <svg viewBox="0 0 128 128" className="size-32 flex-none -rotate-90" role="img" aria-label={`${data.solved} problems solved`}>
      <circle cx="64" cy="64" r={r} fill="none" stroke="var(--raised)" strokeWidth="9" />
      {arcs.map(a => (
        <circle key={a.level} cx="64" cy="64" r={r} fill="none" stroke={LEVEL[a.level].ink} strokeWidth="9" strokeLinecap="butt" strokeDasharray={`${a.dash} ${c}`} strokeDashoffset={-a.offset} />
      ))}
    </svg>
  );
}

/** A year of daily activity, Sunday-first columns, like a contributions grid. */
function Heatmap({ days }: { days: SolvedBoardData['heatmap'] }) {
  const weeks = useMemo(() => {
    if (!days.length) return [];
    const first = new Date(`${days[0].day}T00:00:00`).getDay();
    const cells: ({ day: string; count: number } | null)[] = [...Array(first).fill(null), ...days];
    const out: (typeof cells)[] = [];
    for (let i = 0; i < cells.length; i += 7) out.push(cells.slice(i, i + 7));
    return out;
  }, [days]);
  const max = Math.max(1, ...days.map(d => d.count));
  const tone = (n: number) => (n === 0 ? 0 : n / max < 0.34 ? 1 : n / max < 0.67 ? 2 : 3);
  return (
    <div className="overflow-x-auto pb-1" tabIndex={0} aria-label="Submissions per day over the last year">
      <div className="flex w-max gap-[3px]">
        {weeks.map((week, w) => (
          <div key={w} className="grid grid-rows-7 gap-[3px]">
            {week.map((cell, d) => (
              <span
                key={d}
                title={cell ? `${cell.count} submission${cell.count === 1 ? '' : 's'} on ${cell.day}` : undefined}
                className={cn(
                  'size-[11px] rounded-[3px]',
                  !cell ? 'bg-transparent' : ['bg-raised', 'bg-primary/30', 'bg-primary/60', 'bg-primary'][tone(cell.count)],
                )}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** Solved problems, LeetCode style: only shown on DSA and competitive programming courses. */
export function SolvedBoard({ className, compact = false }: { className?: string; compact?: boolean }) {
  const [data, setData] = useState<SolvedBoardData | null>(null);
  useEffect(() => { api.get<SolvedBoardData>('/library/solved').then(setData).catch(() => setData(null)); }, []);
  if (!data || !data.show) return null;
  return (
    <section className={cn('grid gap-5 paper rounded-card p-5 lg:p-6', className)} aria-labelledby="solved-heading">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="solved-heading" className="font-display text-xl font-semibold tracking-[-0.03em]">Solved</h2>
        <p className="text-[13px] text-muted-foreground tabular-nums">
          {data.acceptance !== null ? `${Math.round(data.acceptance * 100)}% acceptance, ` : ''}{data.submissions} submission{data.submissions === 1 ? '' : 's'}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-6">
        <div className="relative grid place-items-center">
          <Ring data={data} />
          <div className="absolute text-center">
            <p className="font-display text-3xl font-bold tabular-nums leading-none">{data.solved}</p>
            <p className="mt-1 text-[12px] text-muted-foreground tabular-nums">of {data.total.toLocaleString()}</p>
          </div>
        </div>
        <ul className="grid min-w-[200px] flex-1 gap-2.5">
          {data.by_difficulty.map(d => (
            <li key={d.level} className="grid gap-1">
              <div className="flex items-baseline justify-between text-[14px]">
                <span className="font-semibold" style={{ color: LEVEL[d.level].ink }}>{LEVEL[d.level].label}</span>
                <span className="tabular-nums"><span className="font-bold">{d.solved}</span><span className="text-muted-foreground"> / {d.total.toLocaleString()}</span></span>
              </div>
              <span className="h-1.5 overflow-hidden rounded-full bg-raised" aria-hidden="true">
                <span className="block h-full rounded-full" style={{ width: `${d.total ? Math.max(d.solved ? 2 : 0, (100 * d.solved) / d.total) : 0}%`, background: LEVEL[d.level].ink }} />
              </span>
            </li>
          ))}
        </ul>
      </div>
      {compact ? null : (
        <>
          <div className="grid gap-2">
            <p className="flex flex-wrap justify-between gap-2 text-[13px] text-muted-foreground tabular-nums">
              <span>{data.active_days} active day{data.active_days === 1 ? '' : 's'} this year</span>
              <span>Streak {data.streak.current} day{data.streak.current === 1 ? '' : 's'}, best {data.streak.longest}</span>
            </p>
            <Heatmap days={data.heatmap} />
          </div>
          {data.recent.length ? (
            <div>
              <h3 className="mb-2 text-[14px] font-semibold">Recently solved</h3>
              <ul className="grid divide-y text-[14px]">
                {data.recent.map(r => (
                  <li key={`${r.source}:${r.id}`} className="flex min-h-10 items-center justify-between gap-3 py-1.5">
                    {r.source === 'judge'
                      ? <Link href={`/problems/${r.id}`} className="min-w-0 truncate font-medium underline-offset-4 hover:underline">{r.title}</Link>
                      : <span className="min-w-0 truncate font-medium">{r.title}</span>}
                    <span className="flex-none text-[12px] font-semibold" style={{ color: LEVEL[r.level as keyof typeof LEVEL]?.ink }}>{LEVEL[r.level as keyof typeof LEVEL]?.label ?? r.level}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : <p className="text-[14px] text-muted-foreground">Your first accepted solution lands here.</p>}
        </>
      )}
    </section>
  );
}
