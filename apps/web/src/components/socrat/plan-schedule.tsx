'use client';

import Link from 'next/link';
import { useState } from 'react';
import type { ActivityKind, PlanView } from '@/lib/types';
import { KIND_LABEL, NAME, PACE_LABEL, activityHref, formatDate, formatStamp } from '@/lib/routes';
import { cn } from '@/lib/utils';

const DAYS_SHOWN = 4;
const REASONS_SHOWN = 3;
const CHANGES_SHOWN = 2;

/** Lessons carry the accent; checks and practice are quieter so the day reads at a glance. */
const KIND_TONE: Partial<Record<ActivityKind, string>> = {
  lesson: 'bg-primary',
  checkpoint: 'bg-primary',
  quiz: 'bg-primary/55',
  transfer: 'bg-primary/55',
};

function ShowMore({ open, more, onClick, noun }: { open: boolean; more: number; onClick: () => void; noun: string }) {
  if (more <= 0) return null;
  return (
    <button type="button" onClick={onClick} className="justify-self-start text-[14px] font-semibold text-primary underline-offset-4 hover:underline">
      {open ? 'Show less' : `Show ${more} more ${noun}`}
    </button>
  );
}

/** The next study days: a date chip and one line per activity. */
export function NextTwoWeeks({ days }: { days: PlanView['days'] }) {
  const [all, setAll] = useState(false);
  const shown = all ? days : days.slice(0, DAYS_SHOWN);
  return (
    <div className="grid gap-3">
      <ol className="grid gap-1">
        {shown.map((day, index) => {
          const today = index === 0;
          const date = new Date(`${day.date}T00:00:00`);
          return (
            <li key={day.date} className="grid grid-cols-[3rem_1fr] gap-3 rounded-[16px] py-2">
              <div
                className={cn(
                  'grid h-12 w-12 place-content-center rounded-[14px] text-center leading-none',
                  today ? 'bg-primary text-primary-foreground' : 'bg-raised',
                )}
                data-visual-mask=""
                aria-hidden="true"
              >
                <span className="text-[11px] font-semibold uppercase">{today ? NAME.today : date.toLocaleDateString(undefined, { weekday: 'short' })}</span>
                {today ? null : <span className="mt-0.5 font-display text-lg font-semibold tabular-nums">{date.getDate()}</span>}
              </div>
              <div className="min-w-0">
                <p className="flex items-baseline justify-between gap-2 text-[13px] text-muted-foreground">
                  <span className="sr-only">{today ? NAME.today : formatDate(day.date, { weekday: 'long', month: 'short', day: 'numeric' })}: </span>
                  <span className="tabular-nums">{day.minutes} min</span>
                </p>
                <ul className="mt-0.5 grid gap-1">
                  {day.items.map(item => (
                    <li key={item.id} className="flex min-w-0 items-start gap-2 text-[15px] leading-snug">
                      <span className={cn('mt-2 size-1.5 flex-none rounded-full', KIND_TONE[item.kind] ?? 'bg-muted-foreground/40')} aria-hidden="true" />
                      <Link href={activityHref(item.id)} title={item.reason} className="line-clamp-2 min-w-0 break-words underline-offset-4 hover:underline">{item.title}</Link>
                      <span className="sr-only">, {(KIND_LABEL[item.kind] ?? item.kind).toLowerCase()}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          );
        })}
      </ol>
      <ShowMore open={all} more={days.length - DAYS_SHOWN} onClick={() => setAll(a => !a)} noun={days.length - DAYS_SHOWN === 1 ? 'day' : 'days'} />
    </div>
  );
}

/** Why the plan moved: a few short reasons and the latest changes, one line each. */
export function PlanChanges({ reasons, revisions }: { reasons: string[]; revisions: PlanView['revisions'] }) {
  const [all, setAll] = useState(false);
  const shownReasons = all ? reasons : reasons.slice(0, REASONS_SHOWN);
  const shownChanges = all ? revisions : revisions.slice(0, CHANGES_SHOWN);
  const hidden = Math.max(0, reasons.length - REASONS_SHOWN) + Math.max(0, revisions.length - CHANGES_SHOWN);
  return (
    <div className="grid gap-4">
      {shownReasons.length ? (
        <ul className="grid gap-2 text-[15px]">
          {shownReasons.map(r => (
            <li key={r} className="flex gap-2.5">
              <span className="mt-2 size-1.5 flex-none rounded-full bg-primary" aria-hidden="true" />
              <span className={cn(!all && 'line-clamp-2')}>{r}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {shownChanges.length ? (
        <div className="grid gap-1.5">
          <h3 className="text-[13px] font-semibold text-muted-foreground">Recent changes</h3>
          <ol className="grid gap-1.5 border-l-2 border-primary/40 pl-3">
            {shownChanges.map(rev => {
              const added = rev.changes?.added?.length ?? 0;
              const removed = rev.changes?.removed?.length ?? 0;
              return (
                <li key={rev.at} className="text-[14px]">
                  <p className="flex flex-wrap gap-x-2 text-[13px] text-muted-foreground">
                    <span>{formatStamp(rev.at)}</span>
                    <span>{PACE_LABEL[rev.pace]}</span>
                    <span>finish {formatDate(rev.projected_finish, { month: 'short', day: 'numeric' })}</span>
                  </p>
                  {rev.reasons[0] ? <p className={cn(!all && 'line-clamp-1')}>{rev.reasons[0]}</p> : null}
                  {all && (added || removed) ? (
                    <p className="text-[13px] text-muted-foreground">
                      {added ? `Added: ${rev.changes!.added!.join(', ')}. ` : ''}
                      {removed ? `Removed: ${rev.changes!.removed!.join(', ')}.` : ''}
                    </p>
                  ) : added || removed ? (
                    <p className="text-[13px] text-muted-foreground">{[added && `${added} added`, removed && `${removed} removed`].filter(Boolean).join(', ')}</p>
                  ) : null}
                </li>
              );
            })}
          </ol>
        </div>
      ) : null}
      <ShowMore open={all} more={hidden} onClick={() => setAll(a => !a)} noun="details" />
    </div>
  );
}
