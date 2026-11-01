'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api, explain } from '@/lib/api';
import { formatDate, hours } from '@/lib/routes';
import type { Milestone, PathOptions, PathStyle, WeeklyReview } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ProposalList } from '@/components/socrat/proposals';
import { Spinner } from '@/components/ui/spinner';

const YEAR: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' };

/** B4: the same course, four ways to walk it. Choosing one is the learner's own call. */
export function PathStyles({ onChanged }: { onChanged: () => void }) {
  const [options, setOptions] = useState<PathOptions | null>(null);
  const [busy, setBusy] = useState<PathStyle | ''>('');
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<PathOptions>('/adaptive/path-options').then(setOptions).catch(e => setError(explain(e)));
  }, []);

  async function choose(style: PathStyle) {
    setBusy(style);
    setError('');
    try {
      setOptions(await api.post<PathOptions>('/adaptive/path-style', { style }));
      onChanged();
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy('');
    }
  }

  if (error) return <p role="alert" className="text-sm">{error}</p>;
  if (!options) return <Spinner className="size-4" />;
  return (
    <fieldset className="grid gap-2">
      <legend className="sr-only">Path style</legend>
      {options.options.map(o => (
        <label
          key={o.style}
          className={cn(
            'flex cursor-pointer gap-3 rounded-[16px] border bg-raised p-3 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring',
            o.current && 'border-primary ring-1 ring-primary',
          )}
        >
          <input
            type="radio"
            name="path-style"
            className="mt-1 accent-[var(--primary)]"
            checked={o.current}
            disabled={!!busy}
            onChange={() => choose(o.style)}
          />
          <span className="min-w-0">
            <span className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-semibold">{o.label}</span>
              {busy === o.style ? <Spinner className="size-3" /> : null}
            </span>
            <span className="block text-[14px] text-muted-foreground">{o.description}</span>
            <span className="mt-1 block text-[13px] tabular-nums">
              {hours(o.remaining_minutes)} left, finish around {formatDate(o.finish)}
              {o.optional ? `, ${o.optional} optional` : ''}
            </span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}

const SHOWN_WEEKS = 3;
const SHOWN_TOPICS = 3;

/** B3: what each week should finish, and what that lets you do.
 * A quiet timeline: this week leads with its outcome, the next two follow in one line each,
 * and the rest of the path waits behind "Show all weeks". */
export function Milestones({ milestones }: { milestones: Milestone[] }) {
  const [all, setAll] = useState(false);
  if (!milestones.length) return <p className="text-[15px] text-muted-foreground">Everything on your path is done.</p>;
  const shown = all ? milestones : milestones.slice(0, SHOWN_WEEKS);
  const rest = milestones.length - SHOWN_WEEKS;
  return (
    <div className="grid gap-3">
      <ol className="relative grid">
        {shown.map((m, i) => {
          const current = i === 0;
          const extra = m.concepts.length - SHOWN_TOPICS;
          return (
            <li key={m.week} className="relative grid grid-cols-[24px_minmax(0,1fr)] gap-x-3 pb-4 last:pb-0">
              {/* The rail joining the weeks; it stops at the last one shown. */}
              {i < shown.length - 1 ? <span aria-hidden="true" className="absolute top-6 bottom-0 left-[11px] w-px bg-border-strong" /> : null}
              <span
                aria-hidden="true"
                className={cn(
                  'mt-0.5 grid size-6 place-items-center rounded-full text-[12px] font-bold tabular-nums',
                  current ? 'bg-primary text-primary-foreground' : 'border border-border-strong bg-card text-muted-foreground',
                )}
              >
                {m.week}
              </span>
              <div className="min-w-0">
                <p className="flex flex-wrap items-baseline justify-between gap-x-2 text-[13px] text-muted-foreground" data-visual-mask="">
                  <span className={cn(current && 'font-semibold text-foreground')}>{current ? 'This week' : `Week ${m.week}`}</span>
                  <span className="tabular-nums">by {formatDate(m.ends, { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                </p>
                <ul className="mt-1.5 flex flex-wrap gap-1.5" aria-label={`Topics for week ${m.week}`}>
                  {m.concepts.slice(0, SHOWN_TOPICS).map(c => (
                    <li key={c.concept} className="max-w-full truncate rounded-full border border-border px-2.5 py-0.5 text-[13px] font-medium">{c.title}</li>
                  ))}
                  {extra > 0 ? (
                    <li className="rounded-full px-1.5 py-0.5 text-[13px] text-muted-foreground" title={m.concepts.slice(SHOWN_TOPICS).map(c => c.title).join(', ')}>
                      +{extra} more
                    </li>
                  ) : null}
                </ul>
                {current && m.outcome ? <p className="mt-2 text-[14px] leading-snug text-muted-foreground">{m.outcome}</p> : null}
              </div>
            </li>
          );
        })}
      </ol>
      {rest > 0 ? (
        <button type="button" onClick={() => setAll(v => !v)} aria-expanded={all} className="justify-self-start text-[14px] font-semibold underline underline-offset-4">
          {all ? 'Show fewer weeks' : `Show all ${milestones.length} weeks`}
        </button>
      ) : null}
    </div>
  );
}

/** E1: what went well, what is slipping, and the changes waiting for a decision. */
export function WeeklyReviewPanel({ onChanged }: { onChanged: () => void }) {
  const [review, setReview] = useState<WeeklyReview | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get<WeeklyReview>('/adaptive/weekly-review')
      .then(r => {
        setReview(r);
        if (!r.seen) api.post('/adaptive/weekly-review/seen').catch(() => undefined);
      })
      .catch(e => setError(explain(e)));
  }, []);

  if (error) return <p role="alert" className="text-sm">{error}</p>;
  if (!review) return <Spinner className="size-4" />;
  const pct = review.minutes.planned ? Math.round((100 * review.minutes.done) / review.minutes.planned) : 0;
  return (
    <div className="grid gap-4 text-[15px]">
      <p className="text-muted-foreground" data-visual-mask="">
        {formatDate(review.week_start)} to {formatDate(review.week_end)}: {review.minutes.done} of {review.minutes.planned} planned minutes ({pct}%) over {review.study_days} day{review.study_days === 1 ? '' : 's'}.
      </p>
      <section>
        <h3 className="type-label mb-1 text-muted-foreground">What went well</h3>
        <ul className="grid gap-1">{review.wins.map(w => <li key={w}>{w}</li>)}</ul>
      </section>
      {review.stuck.length || review.slipping.length ? (
        <section>
          <h3 className="type-label mb-1 text-muted-foreground">Needs attention</h3>
          <ul className="grid gap-2">
            {review.stuck.map(s => (
              <li key={s.concept}>
                <Link href={s.href} className="font-semibold underline-offset-4 hover:underline">{s.title}</Link>
                <span className="block text-[14px] text-muted-foreground">{s.summary}</span>
              </li>
            ))}
            {review.slipping.map(s => (
              <li key={s.concept}>
                <Link href={s.href} className="font-semibold underline-offset-4 hover:underline">{s.title}</Link>
                <span className="text-[14px] text-muted-foreground">: review overdue and starting to fade</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {review.forecast.target_date ? (
        <p>
          {review.forecast.on_track ? 'On track' : 'Behind'} for {formatDate(review.forecast.target_date, YEAR)}: realistic finish {formatDate(review.forecast.realistic_finish, YEAR)}.
        </p>
      ) : null}
      {review.next_milestone ? (
        <p>
          <span className="font-semibold">Next week:</span> {review.next_milestone.concepts.map(c => c.title).join(', ')}.
        </p>
      ) : null}
      {review.proposals.length ? (
        <section>
          <h3 className="type-label mb-2 text-muted-foreground">Suggested changes</h3>
          <ProposalList compact proposals={review.proposals} onDecided={onChanged} />
        </section>
      ) : null}
    </div>
  );
}
