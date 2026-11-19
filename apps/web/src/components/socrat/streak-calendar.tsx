'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { StreakCalendar as Calendar, StreakDayStatus } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

/**
 * A month of streak days (item 5 of docs/research/duolingo-teardown.md), behind
 * `features.streak_plus`. The server labels each day (learn/streaks.py); this only draws it.
 */
const LABEL: Record<StreakDayStatus, string> = {
  studied: 'studied',
  frozen: 'covered by a freeze',
  saved: 'saved by Socrat',
  repaired: 'earned back',
  missed: 'a study day missed',
  rest: 'a rest day',
  today: 'today',
  planned: 'a study day ahead',
  future: 'a rest day ahead',
  none: 'not started yet',
};

const LOOK: Record<StreakDayStatus, string> = {
  studied: 'border-foreground bg-[var(--highlight)] text-[#15161E] font-bold',
  frozen: 'border-dashed border-foreground',
  saved: 'border-double border-[3px] border-foreground',
  repaired: 'border-foreground underline decoration-2 underline-offset-2',
  missed: 'border-transparent text-muted-foreground line-through decoration-muted-foreground/60',
  rest: 'border-transparent text-muted-foreground',
  today: 'border-foreground border-dotted',
  planned: 'border-dashed border-border-strong text-muted-foreground',
  future: 'border-transparent text-muted-foreground/70',
  none: 'border-transparent text-muted-foreground/50',
};

const LEGEND: StreakDayStatus[] = ['studied', 'frozen', 'saved', 'repaired', 'missed', 'planned'];

function shift(month: string, by: number): string {
  const [y, m] = month.split('-').map(Number);
  const next = new Date(Date.UTC(y, m - 1 + by, 1));
  return next.toISOString().slice(0, 7);
}

export function StreakCalendar() {
  const [month, setMonth] = useState<string | null>(null);
  const [data, setData] = useState<Calendar | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true; // a quick month change must not let an older answer win
    api.get<Calendar>(`/streak/calendar${month ? `?month=${month}` : ''}`)
      .then(v => { if (live) { setData(v); setFailed(false); } })
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [month]);

  if (failed) return <p className="mt-4 text-sm text-muted-foreground">The streak calendar could not load.</p>;
  if (!data) return <div className="mt-4 h-64" aria-busy="true" />;

  const title = new Date(`${data.month}-01T12:00:00`).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  const lead = (new Date(`${data.days[0].day}T12:00:00`).getDay() + 6) % 7; // Monday first
  const weekdays = Array.from({ length: 7 }, (_, i) => new Date(Date.UTC(2026, 10, 2 + i)).toLocaleDateString(undefined, { weekday: 'narrow', timeZone: 'UTC' }));

  return (
    <div className="mt-5 grid max-w-md gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-display text-lg font-semibold" aria-live="polite">{title}</h3>
        <div className="flex gap-1">
          <Button size="sm" variant="ghost" disabled={data.month <= data.earliest} onClick={() => setMonth(shift(data.month, -1))} aria-label="Previous month">Prev</Button>
          <Button size="sm" variant="ghost" disabled={data.month >= data.latest} onClick={() => setMonth(shift(data.month, 1))} aria-label="Next month">Next</Button>
        </div>
      </div>
      <div className="grid grid-cols-7 gap-1.5 text-center" aria-hidden="true">
        {weekdays.map((w, i) => <span key={i} className="text-[12px] text-muted-foreground">{w}</span>)}
      </div>
      <ol className="grid grid-cols-7 gap-1.5" aria-label={`Streak days in ${title}`}>
        {Array.from({ length: lead }, (_, i) => <li key={`pad-${i}`} aria-hidden="true" />)}
        {data.days.map(d => {
          const n = Number(d.day.slice(8));
          const name = new Date(`${d.day}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' });
          return (
            <li key={d.day} className={cn('grid aspect-square place-items-center rounded-full border-2 text-sm tabular-nums', LOOK[d.status])} title={`${name}: ${LABEL[d.status]}${d.minutes ? `, ${d.minutes} min` : ''}`}>
              <span aria-hidden="true">{n}</span>
              <span className="sr-only">{name}: {LABEL[d.status]}{d.minutes ? `, ${d.minutes} minutes` : ''}</span>
            </li>
          );
        })}
      </ol>
      <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[13px] text-muted-foreground" aria-label="Key">
        {LEGEND.map(s => (
          <li key={s} className="flex items-center gap-1.5">
            <span className={cn('inline-block size-4 rounded-full border-2', LOOK[s])} aria-hidden="true" />
            {LABEL[s][0].toUpperCase() + LABEL[s].slice(1)}
          </li>
        ))}
      </ul>
      <p className="text-[13px] text-muted-foreground">Rest days never break a streak. Freezes, saves and earned-back days keep it going but do not count as study.</p>
    </div>
  );
}
