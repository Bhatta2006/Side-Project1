import Link from 'next/link';
import type { Streak } from '@/lib/types';

/**
 * Under the Today streak (features.streak_plus): an earn-back offer, the goal and a way to
 * the calendar. Plain and kind: a missed day is said once, with what brings it back.
 */
export function StreakExtras({ streak }: { streak: Streak }) {
  const back = streak.earn_back;
  const goal = streak.goal;
  const by = back ? new Date(`${back.by}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long' }) : '';
  const left = back ? Math.max(0, back.minutes - back.done_today) : 0;
  return (
    <div className="grid gap-2 text-sm">
      {back ? (
        <p className="rounded-[4px] border-[1.5px] border-foreground/70 px-3 py-2" role="status">
          <span className="font-semibold">Your {back.keep}-day streak can come back.</span>{' '}
          Study {back.minutes} minutes on one day, by {by}{back.done_today ? `; ${left} to go today` : ''}.
        </p>
      ) : null}
      {streak.repaired_today ? <p className="font-semibold" role="status">Streak earned back. Nice work.</p> : null}
      {goal ? (
        <p>
          Goal: {goal.reached ? `${goal.days} days reached.` : `${Math.min(streak.current, goal.days)} of ${goal.days} days.`}
        </p>
      ) : null}
      <Link href="/progress#activity" className="w-fit font-semibold underline underline-offset-4">See your streak calendar</Link>
    </div>
  );
}
