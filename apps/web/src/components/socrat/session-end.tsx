'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { activityHref } from '@/lib/routes';
import type { EndScreen, SessionEndView } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { StampButton } from '@/components/socrat/answer-flow';

/**
 * The end of a session (item 3 of docs/research/duolingo-teardown.md), behind
 * `features.session_end`. The server picks and orders the screens (learn/session_end.py):
 * what the learner proved, then the streak, then the next step. One screen at a time.
 * Calls `onDone` to show the detailed results, straight away if the server has nothing.
 */
export function SessionEnd({ activityId, right, total, onDone }: { activityId: string; right?: number; total?: number; onDone(): void }) {
  const [view, setView] = useState<SessionEndView | null>(null);
  const [step, setStep] = useState(0);
  const asked = useRef('');
  const done = useRef(onDone);
  useEffect(() => { done.current = onDone; });

  useEffect(() => {
    // One request per session end: it records that the streak was shown today.
    if (asked.current === activityId) return;
    asked.current = activityId;
    api.post<SessionEndView>('/session-end', { activity: activityId })
      .then(v => (v.screens.length ? setView(v) : done.current()))
      .catch(() => done.current());
  }, [activityId]);

  if (!view) return <div className="min-h-[50vh]" aria-busy="true" />;
  const screen = view.screens[Math.min(step, view.screens.length - 1)];
  const last = step >= view.screens.length - 1;
  const forward = () => (last ? onDone() : setStep(s => s + 1));

  return (
    <section className="grid min-h-[55vh] content-between gap-8" aria-live="polite" data-arrangement={view.arrangement}>
      <ol className="flex gap-1.5" aria-label={`Step ${step + 1} of ${view.screens.length}`}>
        {view.screens.map((s, i) => (
          <li key={i} className={cn('h-1.5 flex-1 rounded-full', i <= step ? 'bg-foreground' : 'bg-raised')} />
        ))}
      </ol>
      <div key={step} className="animate-in fade-in slide-in-from-bottom-2 duration-200 motion-reduce:animate-none">
        <Screen screen={screen} right={right} total={total} />
      </div>
      <Actions screen={screen} last={last} onForward={forward} onDetails={onDone} />
    </section>
  );
}

const KEPT = { frozen: 'covered by a freeze', saved: 'saved by Socrat', repaired: 'earned back' } as const;

const STATUS: Record<'mastered' | 'shown_alone' | 'building', string> = {
  mastered: 'mastered',
  shown_alone: 'shown on your own',
  building: 'building up',
};

function Screen({ screen, right, total }: { screen: EndScreen; right?: number; total?: number }) {
  const tally = total ? `${right ?? 0} of ${total} right this session.` : null;
  switch (screen.kind) {
    case 'evidence':
      return (
        <div className="grid gap-3">
          <p className="type-label text-muted-foreground">What you proved</p>
          <h1 className="type-display-l text-balance">
            {screen.title ? <>{screen.title}: <span className="hl">{STATUS[screen.status ?? 'building']}</span></> : 'Session complete'}
          </h1>
          {tally ? <p className="text-lg">{tally}</p> : null}
          {screen.title ? (
            <p className="text-[15px] text-muted-foreground">
              On record for this skill: {screen.independent ?? 0} on your own{screen.assisted ? `, ${screen.assisted} with help` : ''}.
              {screen.status === 'mastered' ? ' A review in a few days keeps it.' : ' Socrat counts work done without help as proof.'}
            </p>
          ) : null}
        </div>
      );
    case 'streak':
      return (
        <div className="grid gap-4">
          <p className="type-label text-muted-foreground">{screen.earned_back ? 'Streak earned back' : screen.first_day ? 'Day one' : 'Your streak'}</p>
          <h1 className="type-display-l">
            {screen.current} study {screen.current === 1 ? 'day' : 'days'} in a row
          </h1>
          <ol className="grid max-w-md grid-cols-7 gap-2" aria-label="This week">
            {screen.week.map(d => {
              const label = new Date(`${d.day}T12:00:00`).toLocaleDateString(undefined, { weekday: 'narrow' });
              const name = new Date(`${d.day}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long' });
              return (
                <li key={d.day} className="grid justify-items-center gap-1.5">
                  <span className={cn('grid size-10 place-items-center rounded-full border-2 text-sm font-bold',
                    d.studied ? 'border-foreground bg-[var(--highlight)] text-[#15161E]' : d.kept ? 'border-foreground border-double border-[3px]' : d.scheduled ? 'border-dashed border-border-strong' : 'border-transparent bg-raised/60',
                    d.today && 'ring-2 ring-foreground ring-offset-2 ring-offset-background')}
                  >
                    {d.studied ? <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg> : null}
                  </span>
                  <span className="text-[13px] text-muted-foreground" aria-hidden="true">{label}</span>
                  <span className="sr-only">{name}: {d.studied ? 'studied' : d.kept ? KEPT[d.kept] : d.scheduled ? 'a study day' : 'a rest day'}</span>
                </li>
              );
            })}
          </ol>
          <p className="text-[15px] text-muted-foreground">
            {screen.first_day
              ? 'Come back on your next study day to make it two. Rest days never break it.'
              : screen.milestone
                ? `A milestone. Your longest is ${screen.longest}.`
                : `Your longest is ${screen.longest}. Rest days never break it.`}
            {screen.freezes ? ` ${screen.freezes} ${screen.freezes === 1 ? 'freeze' : 'freezes'} saved for a missed study day.` : ''}
          </p>
          {screen.goal ? (
            <p className="text-[15px]">{screen.goal.reached ? `You reached your ${screen.goal.days}-day goal.` : `Goal: ${Math.min(screen.current, screen.goal.days)} of ${screen.goal.days} days.`}</p>
          ) : null}
        </div>
      );
    case 'badge':
      return (
        <div className="grid gap-3">
          <p className="type-label text-muted-foreground">Badge earned</p>
          <h1 className="type-display-l text-balance">{screen.title}</h1>
          <p className="text-lg">{screen.description}</p>
        </div>
      );
    case 'next':
      return (
        <div className="grid gap-3">
          <p className="type-label text-muted-foreground">{screen.goal_reached ? "Today's goal is done" : 'Up next'}</p>
          <h1 className="type-display-l text-balance">
            {screen.goal_reached ? `${screen.minutes_done} of ${screen.minutes_goal} minutes today` : screen.activity?.title ?? 'Nothing planned right now'}
          </h1>
          {screen.activity ? (
            <p className="text-[15px] text-muted-foreground">
              {screen.goal_reached ? `Next time: ${screen.activity.title}, ${screen.activity.minutes} min.` : `${screen.activity.minutes} min${screen.activity.reason ? ` · ${screen.activity.reason}` : ''}`}
            </p>
          ) : null}
        </div>
      );
  }
}

function Actions({ screen, last, onForward, onDetails }: { screen: EndScreen; last: boolean; onForward(): void; onDetails(): void }) {
  const button = useRef<HTMLButtonElement>(null);
  const link = useRef<HTMLAnchorElement>(null);
  useEffect(() => { (button.current ?? link.current)?.focus({ preventScroll: true }); }, [screen]);
  if (screen.kind === 'next') {
    const next = screen.activity;
    return (
      <div className="flex flex-wrap items-center gap-3">
        {next && !screen.goal_reached ? (
          <Link ref={link} href={activityHref(next.id)} className="stamp">Start</Link>
        ) : (
          <Link ref={link} href="/today" className="stamp">{screen.goal_reached ? 'Done for today' : 'Back to Today'}</Link>
        )}
        {next && screen.goal_reached ? <Button asChild variant="outline" size="lg"><Link href={activityHref(next.id)}>Keep going</Link></Button> : null}
        <Button variant="ghost" size="lg" onClick={onDetails}>See your answers</Button>
      </div>
    );
  }
  if (screen.kind === 'streak' && screen.offer_goal?.length) {
    return <GoalChoice ref={button} goals={screen.offer_goal} again={!!screen.goal?.reached} onDone={onForward} />;
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      <StampButton ref={button} onClick={onForward}>
        {screen.kind === 'streak' && screen.first_day ? "I'll be back" : last ? 'See your answers' : 'Continue'}
      </StampButton>
    </div>
  );
}

/** The day-one commitment (features.streak_plus): pick a streak goal, or not now. */
function GoalChoice({ ref, goals, again, onDone }: { ref: React.Ref<HTMLButtonElement>; goals: (7 | 14 | 30)[]; again: boolean; onDone(): void }) {
  const [busy, setBusy] = useState(false);
  async function pick(days: 7 | 14 | 30) {
    setBusy(true);
    try {
      await api.put('/streak/goal', { days });
    } catch {
      // A goal is a nicety: the session still ends cleanly if it could not be saved.
    } finally {
      onDone();
    }
  }
  return (
    <div className="grid gap-3">
      <p className="text-[15px] font-semibold">{again ? 'Set your next goal?' : 'Commit to a streak goal?'}</p>
      <div className="flex flex-wrap items-center gap-3">
        {goals.map((days, i) =>
          i === 0 ? (
            <StampButton key={days} ref={ref} disabled={busy} onClick={() => void pick(days)}>{days} days</StampButton>
          ) : (
            <Button key={days} variant="outline" size="lg" disabled={busy} onClick={() => void pick(days)}>{days} days</Button>
          ),
        )}
        <Button variant="ghost" size="lg" disabled={busy} onClick={onDone}>Not now</Button>
      </div>
    </div>
  );
}
